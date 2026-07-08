# ===================================================================
# ZEMmacOS - IDM STYLE DOWNLOADER (RESUME FIXED)
# ===================================================================
import os
import threading
import time
import json
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

class IDMDownloader:
    """Multi-threaded download manager with pause/resume support"""
    
    def __init__(self, callback=None, num_threads=8):
        self.callback = callback
        self.num_threads = num_threads
        self.active_downloads = {}  # {url: download_info}
        self.paused = set()          # Set of paused URLs
        self.cancelled = set()       # Set of cancelled URLs
        self.lock = threading.Lock()

    # -----------------------------------------------------------------
    # PROGRESS CALLBACK
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

    # -----------------------------------------------------------------
    # URL CHECKING
    # -----------------------------------------------------------------
    def _get_file_size(self, url, headers=None):
        try:
            response = requests.head(url, headers=headers or {}, timeout=10, allow_redirects=True)
            if response.status_code == 200:
                return int(response.headers.get('Content-Length', -1))
            elif response.status_code in (301, 302):
                return self._get_file_size(response.headers.get('Location', url), headers)
            return -1
        except Exception as e:
            self._send_log(f"Failed to get file size: {e}", "error")
            return -1

    def _check_url(self, url, headers=None):
        try:
            response = requests.head(url, headers=headers or {}, timeout=10, allow_redirects=True)
            if response.status_code == 200:
                supports_range = response.headers.get('Accept-Ranges', '').lower() == 'bytes'
                return True, supports_range, response.headers.get('Content-Length', -1)
            elif response.status_code in (301, 302):
                return self._check_url(response.headers.get('Location', url), headers)
            return False, False, -1
        except Exception as e:
            self._send_log(f"URL check failed: {e}", "error")
            raise

    # -----------------------------------------------------------------
    # SEGMENT DOWNLOAD
    # -----------------------------------------------------------------
    def _download_segment(self, url, start_byte, end_byte, part_file, segment_id, headers=None, 
                          download_id=None, total_size=None):
        try:
            range_header = {'Range': f'bytes={start_byte}-{end_byte}'}
            if headers:
                range_header.update(headers)
            
            response = requests.get(url, headers=range_header, stream=True, timeout=30)
            if response.status_code not in (200, 206):
                self._send_log(f"Segment {segment_id} failed: HTTP {response.status_code}", "error")
                return False, 0
            
            bytes_written = 0
            last_update = time.time()
            
            # Check if part file exists and has content (for resume)
            if os.path.exists(part_file):
                bytes_written = os.path.getsize(part_file)
                # If already complete, skip
                if bytes_written >= (end_byte - start_byte + 1):
                    return True, bytes_written

            with open(part_file, 'ab') as f: # Append mode for resume
                for chunk in response.iter_content(chunk_size=8192):
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
                            if now - last_update >= 0.3:
                                with self.lock:
                                    if download_id in self.active_downloads:
                                        # Note: We don't increment active_downloads[download_id]["downloaded_bytes"] here
                                        # because we are calculating total progress from scratch in the main loop
                                        # to avoid double counting or race conditions during resume.
                                        pass
                                last_update = now
            return True, bytes_written
        except Exception as e:
            self._send_log(f"Segment {segment_id} error: {e}", "error")
            raise

    # -----------------------------------------------------------------
    # MAIN DOWNLOAD METHOD
    # -----------------------------------------------------------------
    def download(self, url, filename, save_dir, headers=None):
        download_id = url
        
        with self.lock:
            # If already running and not paused, reject
            if download_id in self.active_downloads:
                if self.active_downloads[download_id].get("status") != "paused":
                    return {"status": "already_running", "filepath": None, "error": None}
                # If paused, remove from paused set but keep active_downloads entry
                self.paused.discard(url)
                self._send_log("Resuming paused download...", "info")

            # Initialize or reset state for this download
            self.active_downloads[download_id] = {
                "url": url,
                "filename": filename,
                "save_dir": save_dir,
                "headers": headers,
                "start_time": time.time(),
                "total_bytes": 0,
                "downloaded_bytes": 0,
                "status": "starting"
            }

        try:
            os.makedirs(save_dir, exist_ok=True)
            filepath = os.path.join(save_dir, filename)
            state_file = filepath + '.idmstate'
            part_dir = filepath + '.parts'
            
            # Check for existing state to resume
            resume_data = None
            if os.path.exists(state_file):
                try:
                    with open(state_file, 'r') as f:
                        resume_data = json.load(f)
                    self._send_log(f"Found state file. Resuming...", "info")
                except:
                    pass
            
            # Get file size
            valid, supports_range, content_length = self._check_url(url, headers)
            if not valid:
                raise Exception("URL returned invalid response")
            
            total_size = int(content_length) if content_length != -1 else -1
            
            if total_size == -1 or not supports_range:
                self._send_log("Server doesn't support range requests - using single thread", "warning")
                return self._single_thread_download(url, filepath, headers)

            self._send_log(f"File size: {self._format_size(total_size)}", "info")
            
            # Calculate segments
            segment_size = total_size // self.num_threads
            segments = []
            for i in range(self.num_threads):
                start = i * segment_size
                end = (i + 1) * segment_size - 1 if i < self.num_threads - 1 else total_size - 1
                segments.append((start, end, i))
            
            os.makedirs(part_dir, exist_ok=True)
            
            # Load existing progress
            completed_segments = set()
            downloaded_so_far = 0
            
            if resume_data and resume_data.get('segments'):
                completed_segments = set(resume_data['segments'])
                downloaded_so_far = resume_data.get('downloaded_bytes', 0)
                self._send_log(f"Resuming from {self._format_size(downloaded_so_far)}", "info")
            else:
                # If no state file, check if part files exist to calculate progress
                for i in range(len(segments)):
                    part_file = os.path.join(part_dir, f"part_{i}")
                    if os.path.exists(part_file):
                        size = os.path.getsize(part_file)
                        downloaded_so_far += size
                        # If part file is full size, mark as completed
                        start, end, _ = segments[i]
                        if size >= (end - start + 1):
                            completed_segments.add(i)
                if downloaded_so_far > 0:
                    self._send_log(f"Recovered partial progress: {self._format_size(downloaded_so_far)}", "info")

            if download_id in self.cancelled:
                raise Exception("Download cancelled before start")
            
            # Update active download state
            with self.lock:
                self.active_downloads[download_id].update({
                    "total_bytes": total_size,
                    "downloaded_bytes": downloaded_so_far,
                    "status": "downloading"
                })
            
            self._send_progress(download_id, downloaded_so_far, total_size)
            
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
                
                last_update = time.time()
                last_downloaded = downloaded_so_far
                
                while futures:
                    # Check for cancellation/pause
                    if download_id in self.cancelled:
                        executor.shutdown(wait=False, cancel_futures=True)
                        return {"status": "cancelled", "filepath": None, "error": None}
                    
                    if download_id in self.paused:
                        # Save current state
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
                            self.active_downloads[download_id]["status"] = "paused"
                        self._send_log("Download paused - state saved", "warning")
                        return {"status": "paused", "filepath": None, "error": None}
                    
                    # Check for completed futures
                    done_futures = [f for f in futures if f.done()]
                    for future in done_futures:
                        seg_id, part_file, start, end = futures.pop(future)
                        success, bytes_downloaded = future.result()
                        
                        if success:
                            completed_segments.add(seg_id)
                            
                            # Recalculate total downloaded from all parts to ensure accuracy
                            current_total_downloaded = 0
                            for s_start, s_end, s_id in segments:
                                p_file = os.path.join(part_dir, f"part_{s_id}")
                                if os.path.exists(p_file):
                                    current_total_downloaded += os.path.getsize(p_file)
                            
                            downloaded_so_far = current_total_downloaded
                            
                            # Update state
                            with self.lock:
                                if download_id in self.active_downloads:
                                    self.active_downloads[download_id]["downloaded_bytes"] = downloaded_so_far
                            
                            now = time.time()
                            if now - last_update >= 0.3:
                                elapsed = now - self.active_downloads[download_id]["start_time"]
                                speed = (downloaded_so_far - last_downloaded) / (now - last_update) if (now - last_update) > 0 else 0
                                eta = (total_size - downloaded_so_far) / speed if speed > 0 else 0
                                
                                self._send_progress(download_id, downloaded_so_far, total_size, speed, eta)
                                last_update = now
                                last_downloaded = downloaded_so_far
                            
                            # Save state periodically
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
                        else:
                            self._send_log(f"Segment {seg_id} failed", "error")
                            # Optionally retry or fail whole download. For now, fail.
                            raise Exception(f"Segment {seg_id} download failed")
                    
                    time.sleep(0.05) # Small sleep to prevent CPU spinning

            # All segments completed
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
            self._send_log(f"Download failed: {e}", "error")
            with self.lock:
                if download_id in self.active_downloads:
                    self.active_downloads[download_id]["status"] = "failed"
            return {"status": "failed", "filepath": None, "error": str(e)}
        finally:
            with self.lock:
                if download_id in self.cancelled:
                    self.cancelled.discard(download_id)
                    # Don't pop immediately if we want to inspect state, but usually clean up
                    if download_id in self.active_downloads:
                        del self.active_downloads[download_id]

    # -----------------------------------------------------------------
    # SINGLE THREAD FALLBACK
    # -----------------------------------------------------------------
    def _single_thread_download(self, url, filepath, headers=None):
        try:
            # Check for resume
            start_byte = 0
            if os.path.exists(filepath):
                start_byte = os.path.getsize(filepath)
            
            range_header = {}
            if start_byte > 0:
                range_header['Range'] = f'bytes={start_byte}-'
            if headers:
                range_header.update(headers)

            response = requests.get(url, headers=range_header, stream=True, timeout=30)
            total_size = int(response.headers.get('Content-Length', -1))
            if total_size != -1 and start_byte > 0:
                total_size = total_size # Keep original total for progress calculation
            
            downloaded = start_byte
            last_update = time.time()
            start_time = time.time()
            
            mode = 'ab' if start_byte > 0 else 'wb'
            with open(filepath, mode) as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if url in self.cancelled:
                        return {"status": "cancelled", "filepath": None, "error": None}
                    if url in self.paused:
                        # Save state for single thread
                        state_data = {
                            'downloaded_bytes': downloaded,
                            'total_bytes': total_size,
                            'filename': os.path.basename(filepath),
                            'url': url
                        }
                        # Single thread doesn't use segments, so we save differently or just rely on file size
                        return {"status": "paused", "filepath": None, "error": None}
                    
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        now = time.time()
                        if now - last_update >= 0.3:
                            elapsed = now - start_time
                            speed = (downloaded - start_byte) / elapsed if elapsed > 0 else 0
                            eta = (total_size - downloaded) / speed if speed > 0 else 0
                            self._send_progress(url, downloaded, total_size, speed, eta)
                            last_update = now
            
            self._send_progress(url, total_size, total_size, final=True)
            return {"status": "completed", "filepath": filepath, "error": None}
        except Exception as e:
            return {"status": "failed", "filepath": None, "error": str(e)}

    # -----------------------------------------------------------------
    # UTILS
    # -----------------------------------------------------------------
    def _merge_segments(self, part_dir, output_file, total_size, num_threads):
        with open(output_file, 'wb') as outfile:
            for i in range(num_threads):
                part_file = os.path.join(part_dir, f"part_{i}")
                if os.path.exists(part_file):
                    with open(part_file, 'rb') as infile:
                        outfile.write(infile.read())

    def _cleanup(self, part_dir, state_file):
        try:
            if os.path.exists(part_dir):
                import shutil
                shutil.rmtree(part_dir)
            if os.path.exists(state_file):
                os.remove(state_file)
        except:
            pass

    # -----------------------------------------------------------------
    # CONTROL METHODS
    # -----------------------------------------------------------------
    def pause(self, url):
        with self.lock:
            self.paused.add(url)
            if url in self.active_downloads:
                self.active_downloads[url]["status"] = "paused"
        self._send_log("⏸️ Pause signal sent - download will stop shortly", "warning")

    def resume(self, url, filename, save_dir, headers=None):
        # Just call download. The download method checks for existing state/paused status.
        # We do NOT delete from active_downloads here anymore.
        return self.download(url, filename, save_dir, headers)

    def cancel(self, url):
        with self.lock:
            self.cancelled.add(url)
            if url in self.active_downloads:
                self.active_downloads[url]["status"] = "cancelled"
        self._send_log("❌ Cancel signal sent - cleaning up...", "warning")
        time.sleep(0.5)
        with self.lock:
            if url in self.active_downloads:
                info = self.active_downloads[url]
                filepath = os.path.join(info.get("save_dir", ""), info.get("filename", ""))
                part_dir = filepath + '.parts'
                state_file = filepath + '.idmstate'
                try:
                    import shutil
                    if os.path.exists(part_dir): shutil.rmtree(part_dir)
                    if os.path.exists(state_file): os.remove(state_file)
                except:
                    pass

    def clear_state(self, url):
        with self.lock:
            self.active_downloads.pop(url, None)
            self.cancelled.discard(url)
            self.paused.discard(url)

    def is_paused(self, url):
        with self.lock: return url in self.paused

    def is_cancelled(self, url):
        with self.lock: return url in self.cancelled

    def get_status(self, url):
        with self.lock: return self.active_downloads.get(url, {}).copy()

    def _format_size(self, bytes_size):
        if bytes_size <= 0: return "0 B"
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_size < 1024.0: return f"{bytes_size:.1f} {unit}"
            bytes_size /= 1024.0
        return f"{bytes_size:.1f} PB"

    def _format_time(self, seconds):
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}" if hours > 0 else f"{minutes:02d}:{secs:02d}"