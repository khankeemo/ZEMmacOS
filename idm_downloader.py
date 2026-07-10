# ===================================================================
# ZEMmacOS - IDM STYLE DOWNLOADER
# ===================================================================
import os
import threading
import time
import json
import requests
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta

NETWORK_ERRORS = (
    requests.exceptions.ConnectionError,
    requests.exceptions.Timeout,
    requests.exceptions.ReadTimeout,
    requests.exceptions.ConnectTimeout,
    requests.exceptions.ChunkedEncodingError,
    ConnectionResetError,
    ConnectionAbortedError,
    ConnectionError,
    TimeoutError,
    OSError,
)


def _is_network_error(exc):
    name = type(exc).__name__.lower()
    keywords = ["connectionerror", "timeout", "connection", "reset",
                "refused", "resolve", "network", "eof", "read timed out",
                "chunkedencodingerror", "remotedisconnected",
                "connectionabortederror", "connectionreseterror"]
    return any(k in name for k in keywords) or isinstance(exc, NETWORK_ERRORS)


def probe_optimal_threads(url, headers=None, probe_bytes=4*1024*1024):
    """Download first probe_bytes with 1,2,4,8,16 threads concurrently, return fastest count."""
    best = 8
    best_speed = 0

    def _test(nt):
        nonlocal best, best_speed
        seg_size = probe_bytes // nt
        ret = []
        s = requests.Session()
        s.headers.update({"User-Agent": "Mozilla/5.0 ZEMmacOS Probe"})

        def work(seg_id, start, end):
            try:
                h = {"Range": f"bytes={start}-{end}"}
                r = s.get(url, headers=h, stream=True, timeout=15)
                w = 0
                for c in r.iter_content(chunk_size=262144):
                    if c:
                        w += len(c)
                ret.append(w)
            except Exception:
                ret.append(0)

        t0 = time.time()
        threads = []
        for i in range(nt):
            s_start = i * seg_size
            s_end = (i + 1) * seg_size - 1 if i < nt - 1 else probe_bytes - 1
            t = threading.Thread(target=lambda i=i, s=s_start, e=s_end: work(i, s, e))
            t.start()
            threads.append(t)
        for t in threads:
            t.join(timeout=15)
        elapsed = time.time() - t0
        total = sum(ret)
        speed = total / elapsed if elapsed > 0 else 0
        if speed > best_speed:
            best_speed = speed
            best = nt

    probe_threads = []
    for nt in [1, 2, 4, 8, 16]:
        t = threading.Thread(target=_test, args=(nt,))
        t.start()
        probe_threads.append(t)
    for t in probe_threads:
        t.join(timeout=25)
    return best


class IDMDownloader:
    """Multi-threaded download manager with pause/resume support"""

    def __init__(self, callback=None, num_threads=8):
        self.callback = callback
        self.num_threads = num_threads
        self.active_downloads = {}
        self.paused = set()
        self.cancelled = set()
        self.lock = threading.Lock()
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": "Mozilla/5.0 ZEMmacOS Downloader"})

    # -----------------------------------------------------------------
    # CALLBACK HELPERS
    # -----------------------------------------------------------------
    def _send_progress(self, download_id, downloaded, total, speed=0, eta=0, final=False):
        if self.callback:
            percentage = (downloaded / total * 100) if total > 0 else 0
            download_info = self.active_downloads.get(download_id, {})
            try:
                self.callback({
                    "type": "progress",
                    "percentage": percentage,
                    "downloaded": downloaded,
                    "total": total,
                    "speed": speed,
                    "eta": eta,
                    "filename": download_info.get("filename", "Unknown"),
                    "status": "completed" if final else "downloading"
                })
            except Exception as e:
                print(f"Callback error: {e}")

    def _send_log(self, message, level="info"):
        if self.callback:
            try:
                self.callback({"type": "log", "message": message, "level": level})
            except Exception as e:
                print(f"Log callback error: {e}")

    def _get_active(self, download_id):
        with self.lock:
            return self.active_downloads.get(download_id)

    # -----------------------------------------------------------------
    # URL CHECKING
    # -----------------------------------------------------------------
    def _get_file_size(self, url, headers=None):
        try:
            response = self._session.head(url, headers=headers or {}, timeout=10, allow_redirects=True)
            if response.status_code == 200:
                return int(response.headers.get('Content-Length', -1))
            return -1
        except Exception as e:
            self._send_log(f"Failed to get file size: {e}", "error")
            return -1

    def _check_url(self, url, headers=None):
        try:
            response = self._session.head(url, headers=headers or {}, timeout=10, allow_redirects=True)
            if response.status_code == 200:
                supports_range = 'bytes' in response.headers.get('Accept-Ranges', '').lower()
                return True, supports_range, int(response.headers.get('Content-Length', -1))
            return False, False, -1
        except Exception as e:
            self._send_log(f"URL check failed: {e}", "error")
            raise

    # -----------------------------------------------------------------
    # SEGMENT DOWNLOAD
    # -----------------------------------------------------------------
    def _download_segment(self, url, start_byte, end_byte, part_file, segment_id, headers=None,
                          download_id=None, total_size=None):
        max_retries = 3
        for attempt in range(1, max_retries + 1):
            try:
                range_header = {'Range': f'bytes={start_byte}-{end_byte}'}
                if headers:
                    range_header.update(headers)

                response = self._session.get(url, headers=range_header, stream=True, timeout=60)
                if response.status_code not in (200, 206):
                    self._send_log(f"Segment {segment_id} failed: HTTP {response.status_code}", "error")
                    if attempt < max_retries:
                        time.sleep(1)
                        continue
                    return False, 0

                bytes_written = 0
                last_update = time.time()
                last_reported = 0

                if os.path.exists(part_file):
                    bytes_written = os.path.getsize(part_file)
                    last_reported = bytes_written
                    if bytes_written >= (end_byte - start_byte + 1):
                        return True, bytes_written

                with open(part_file, 'ab') as f:
                    for chunk in response.iter_content(chunk_size=262144):
                        if download_id:
                            with self.lock:
                                if download_id in self.cancelled:
                                    return False, bytes_written
                                if download_id in self.paused:
                                    return False, bytes_written

                        if chunk:
                            f.write(chunk)
                            bytes_written += len(chunk)

                            if download_id and total_size:
                                now = time.time()
                                if now - last_update >= 1.0:
                                    delta = bytes_written - last_reported
                                    with self.lock:
                                        if download_id in self.active_downloads:
                                            self.active_downloads[download_id]["downloaded_bytes"] += delta
                                    last_reported = bytes_written
                                    last_update = now
                return True, bytes_written
            except Exception as e:
                self._send_log(f"Segment {segment_id} attempt {attempt}/{max_retries}: {e}", "error")
                if _is_network_error(e):
                    if attempt < max_retries:
                        time.sleep(2)
                        continue
                    return "network_loss", 0
                raise

    # -----------------------------------------------------------------
    # MAIN DOWNLOAD METHOD
    # -----------------------------------------------------------------
    def download(self, url, filename, save_dir, headers=None):
        download_id = url

        with self.lock:
            if download_id in self.active_downloads:
                existing = self.active_downloads[download_id]
                status = existing.get("status")
                if status == "paused":
                    self.paused.discard(url)
                    self._send_log("Resuming paused download...", "info")
                elif status == "downloading":
                    return {"status": "already_running", "filepath": None, "error": None}
                elif status in ("network_error", "failed", "completed", "cancelled"):
                    self.active_downloads[download_id] = {
                        "url": url, "filename": filename, "save_dir": save_dir,
                        "headers": headers, "start_time": time.time(),
                        "total_bytes": 0, "downloaded_bytes": 0, "status": "starting"
                    }
                    self._send_log(f"Starting fresh download ({status})...", "info")
                else:
                    return {"status": "already_running", "filepath": None, "error": None}
            else:
                self.active_downloads[download_id] = {
                    "url": url, "filename": filename, "save_dir": save_dir,
                    "headers": headers, "start_time": time.time(),
                    "total_bytes": 0, "downloaded_bytes": 0, "status": "starting"
                }

        try:
            os.makedirs(save_dir, exist_ok=True)
            filepath = os.path.join(save_dir, filename)
            state_file = filepath + '.idmstate'
            part_dir = filepath + '.parts'

            resume_data = None
            if os.path.exists(state_file):
                try:
                    with open(state_file, 'r') as f:
                        resume_data = json.load(f)
                    self._send_log("Found state file. Resuming...", "info")
                except Exception:
                    pass

            valid, supports_range, content_length = self._check_url(url, headers)
            if not valid:
                raise Exception("URL returned invalid response")

            total_size = int(content_length) if content_length != -1 else -1

            if total_size == -1 or not supports_range:
                self._send_log("Server doesn't support range requests - using single thread", "warning")
                return self._single_thread_download(url, filepath, headers)

            self._send_log(f"File size: {self._format_size(total_size)}", "info")

            segment_size = total_size // self.num_threads
            segments = []
            for i in range(self.num_threads):
                start = i * segment_size
                end = (i + 1) * segment_size - 1 if i < self.num_threads - 1 else total_size - 1
                segments.append((start, end, i))

            os.makedirs(part_dir, exist_ok=True)

            completed_segments = set()
            downloaded_so_far = 0

            if resume_data and resume_data.get('segments'):
                completed_segments = set(resume_data['segments'])
                downloaded_so_far = resume_data.get('downloaded_bytes', 0)
                self._send_log(f"Resuming from {self._format_size(downloaded_so_far)}", "info")
            else:
                for i in range(len(segments)):
                    part_file = os.path.join(part_dir, f"part_{i}")
                    if os.path.exists(part_file):
                        size = os.path.getsize(part_file)
                        downloaded_so_far += size
                        start, end, _ = segments[i]
                        if size >= (end - start + 1):
                            completed_segments.add(i)
                if downloaded_so_far > 0:
                    self._send_log(f"Recovered partial progress: {self._format_size(downloaded_so_far)}", "info")

            if download_id in self.cancelled:
                raise Exception("Download cancelled before start")

            with self.lock:
                self.active_downloads[download_id].update({
                    "total_bytes": total_size,
                    "downloaded_bytes": downloaded_so_far,
                    "status": "downloading"
                })

            self._send_progress(download_id, downloaded_so_far, total_size)

            progress_stop = threading.Event()

            def progress_reporter():
                last_bytes = downloaded_so_far
                last_time = time.time()
                speed_samples = []
                while not progress_stop.is_set():
                    time.sleep(1.0)
                    with self.lock:
                        if download_id not in self.active_downloads:
                            break
                        info = self.active_downloads[download_id]
                        current = info.get("downloaded_bytes", downloaded_so_far)
                        total = info.get("total_bytes", total_size)
                        status = info.get("status", "downloading")
                    if status == "paused" or status == "cancelled":
                        break
                    now = time.time()
                    elapsed = now - last_time
                    inst_speed = (current - last_bytes) / elapsed if elapsed > 0 else 0
                    if inst_speed > 0:
                        speed_samples.append(inst_speed)
                        if len(speed_samples) > 5:
                            speed_samples.pop(0)
                    speed = sum(speed_samples) / len(speed_samples) if speed_samples else inst_speed
                    eta = (total - current) / speed if speed > 0 else 0
                    last_bytes = current
                    last_time = now
                    self._send_progress(download_id, current, total, speed, eta)

            reporter_thread = threading.Thread(target=progress_reporter, daemon=True)
            reporter_thread.start()

            network_lost = False
            with ThreadPoolExecutor(max_workers=self.num_threads) as executor:
                futures = {}
                for start, end, seg_id in segments:
                    if seg_id in completed_segments:
                        continue
                    part_file = os.path.join(part_dir, f"part_{seg_id}")
                    future = executor.submit(
                        self._download_segment,
                        url, start, end, part_file, seg_id, headers,
                        download_id, total_size
                    )
                    futures[future] = (seg_id, part_file, start, end)

                while futures:
                    if download_id in self.cancelled:
                        executor.shutdown(wait=False, cancel_futures=True)
                        progress_stop.set()
                        reporter_thread.join(timeout=1)
                        return {"status": "cancelled", "filepath": None, "error": None}

                    if download_id in self.paused:
                        current_total = 0
                        for s_start, s_end, s_id in segments:
                            p_file = os.path.join(part_dir, f"part_{s_id}")
                            if os.path.exists(p_file):
                                current_total += os.path.getsize(p_file)
                        downloaded_so_far = current_total
                        state_data = {
                            'segments': list(completed_segments),
                            'downloaded_bytes': downloaded_so_far,
                            'total_bytes': total_size,
                            'num_threads': self.num_threads,
                            'filename': filename,
                            'url': url
                        }
                        with open(state_file, 'w') as f:
                            json.dump(state_data, f)
                        with self.lock:
                            self.active_downloads[download_id]["downloaded_bytes"] = downloaded_so_far
                            self.active_downloads[download_id]["status"] = "paused"
                        self._send_log("Download paused - state saved", "warning")
                        progress_stop.set()
                        executor.shutdown(wait=False, cancel_futures=True)
                        reporter_thread.join(timeout=1)
                        return {"status": "paused", "filepath": None, "error": None}

                    done = [f for f in futures if f.done()]
                    for future in done:
                        seg_id, part_file, start, end = futures.pop(future)
                        try:
                            success, _ = future.result()
                        except Exception:
                            success = False

                        if success is True:
                            completed_segments.add(seg_id)
                            current_total = 0
                            for s_start, s_end, s_id in segments:
                                p_file = os.path.join(part_dir, f"part_{s_id}")
                                if os.path.exists(p_file):
                                    current_total += os.path.getsize(p_file)
                            downloaded_so_far = current_total
                            with self.lock:
                                if download_id in self.active_downloads:
                                    self.active_downloads[download_id]["downloaded_bytes"] = downloaded_so_far
                            state_data = {
                                'segments': list(completed_segments),
                                'downloaded_bytes': downloaded_so_far,
                                'total_bytes': total_size,
                                'num_threads': self.num_threads,
                                'filename': filename,
                                'url': url
                            }
                            with open(state_file, 'w') as f:
                                json.dump(state_data, f)
                        elif success == "network_loss":
                            network_lost = True
                            break
                        else:
                            self._send_log(f"Segment {seg_id} failed", "error")
                            network_lost = True
                            break

                    if network_lost:
                        executor.shutdown(wait=False, cancel_futures=True)
                        progress_stop.set()
                        reporter_thread.join(timeout=1)
                        with self.lock:
                            if download_id in self.active_downloads:
                                self.active_downloads[download_id]["status"] = "network_error"
                        return {"status": "network_error", "filepath": None, "error": "Network connection lost"}

                    time.sleep(0.05)

            progress_stop.set()
            reporter_thread.join(timeout=1)

            if download_id not in self.cancelled and download_id not in self.paused:
                self._send_log("Merging segments...", "info")
                self._merge_segments(part_dir, filepath, total_size, self.num_threads)
                self._cleanup(part_dir, state_file)

                elapsed = time.time() - self.active_downloads[download_id]["start_time"]
                self._send_log(f"Download complete! ({self._format_size(total_size)} in {self._format_time(elapsed)})", "success")

                with self.lock:
                    self.active_downloads[download_id]["status"] = "completed"

                self._send_progress(download_id, total_size, total_size, final=True)
                return {"status": "completed", "filepath": filepath, "error": None}

            return {"status": "cancelled", "filepath": None, "error": None}

        except Exception as e:
            is_net = _is_network_error(e)
            self._send_log(f"Download {'network error' if is_net else 'failed'}: {e}", "error")
            with self.lock:
                if download_id in self.active_downloads:
                    self.active_downloads[download_id]["status"] = "network_error" if is_net else "failed"
            return {"status": "network_error" if is_net else "failed", "filepath": None, "error": str(e)}
        finally:
            with self.lock:
                if download_id in self.cancelled:
                    self.cancelled.discard(download_id)
                    if download_id in self.active_downloads:
                        del self.active_downloads[download_id]

    # -----------------------------------------------------------------
    # SINGLE THREAD FALLBACK
    # -----------------------------------------------------------------
    def _single_thread_download(self, url, filepath, headers=None):
        try:
            start_byte = 0
            if os.path.exists(filepath):
                start_byte = os.path.getsize(filepath)

            range_header = {}
            if start_byte > 0:
                range_header['Range'] = f'bytes={start_byte}-'
            if headers:
                range_header.update(headers)

            response = self._session.get(url, headers=range_header, stream=True, timeout=60)
            total_size = int(response.headers.get('Content-Length', -1))

            downloaded = start_byte
            last_update = time.time()
            start_time = time.time()

            mode = 'ab' if start_byte > 0 else 'wb'
            with open(filepath, mode) as f:
                for chunk in response.iter_content(chunk_size=262144):
                    if url in self.cancelled:
                        return {"status": "cancelled", "filepath": None, "error": None}
                    if url in self.paused:
                        return {"status": "paused", "filepath": None, "error": None}

                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        now = time.time()
                        if now - last_update >= 1.0:
                            elapsed = now - start_time
                            speed = (downloaded - start_byte) / elapsed if elapsed > 0 else 0
                            eta = (total_size - downloaded) / speed if speed > 0 else 0
                            self._send_progress(url, downloaded, total_size, speed, eta)
                            last_update = now

            self._send_progress(url, total_size, total_size, final=True)
            return {"status": "completed", "filepath": filepath, "error": None}
        except Exception as e:
            is_net = _is_network_error(e)
            return {"status": "network_error" if is_net else "failed", "filepath": None, "error": str(e)}

    # -----------------------------------------------------------------
    # UTILS
    # -----------------------------------------------------------------
    def _merge_segments(self, part_dir, output_file, total_size, num_threads):
        with open(output_file, 'wb') as outfile:
            for i in range(num_threads):
                part_file = os.path.join(part_dir, f"part_{i}")
                if os.path.exists(part_file):
                    with open(part_file, 'rb') as infile:
                        while True:
                            buf = infile.read(1048576)
                            if not buf:
                                break
                            outfile.write(buf)

    def _cleanup(self, part_dir, state_file):
        try:
            if os.path.exists(part_dir):
                import shutil
                shutil.rmtree(part_dir)
            if os.path.exists(state_file):
                os.remove(state_file)
        except Exception:
            pass

    # -----------------------------------------------------------------
    # CONTROL METHODS
    # -----------------------------------------------------------------
    def pause(self, url):
        with self.lock:
            self.paused.add(url)
            if url in self.active_downloads:
                self.active_downloads[url]["status"] = "paused"
        self._send_log("Pause signal sent - download will stop shortly", "warning")

    def resume(self, url, filename, save_dir, headers=None):
        return self.download(url, filename, save_dir, headers)

    def cancel(self, url):
        with self.lock:
            self.cancelled.add(url)
            if url in self.active_downloads:
                self.active_downloads[url]["status"] = "cancelled"
        self._send_log("Cancel signal sent - cleaning up...", "warning")
        threading.Thread(target=self._cleanup_cancelled, args=(url,), daemon=True).start()

    def _cleanup_cancelled(self, url):
        time.sleep(0.5)
        with self.lock:
            if url in self.active_downloads:
                info = self.active_downloads[url]
                filepath = os.path.join(info.get("save_dir", ""), info.get("filename", ""))
                part_dir = filepath + '.parts'
                state_file = filepath + '.idmstate'
                try:
                    import shutil
                    if os.path.exists(part_dir):
                        shutil.rmtree(part_dir)
                    if os.path.exists(state_file):
                        os.remove(state_file)
                except Exception:
                    pass

    def clear_state(self, url):
        with self.lock:
            self.active_downloads.pop(url, None)
            self.cancelled.discard(url)
            self.paused.discard(url)

    def is_paused(self, url):
        with self.lock:
            return url in self.paused

    def is_cancelled(self, url):
        with self.lock:
            return url in self.cancelled

    def get_status(self, url):
        with self.lock:
            return self.active_downloads.get(url, {}).copy()

    def _format_size(self, bytes_size):
        if bytes_size <= 0:
            return "0 B"
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_size < 1024.0:
                return f"{bytes_size:.1f} {unit}"
            bytes_size /= 1024.0
        return f"{bytes_size:.1f} PB"

    def _format_time(self, seconds):
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}" if hours > 0 else f"{minutes:02d}:{secs:02d}"