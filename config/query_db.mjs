import { Pool } from 'pg';
import fs from 'fs';

const env = fs.readFileSync('D:\\websmith\\.env.local', 'utf8');
const match = env.match(/DATABASE_URL='(.+?)'/);
if (!match) { console.error('No DATABASE_URL found'); process.exit(1); }

const pool = new Pool({ connectionString: match[1], ssl: { rejectUnauthorized: false } });

const plans = await pool.query("SELECT name FROM plans WHERE product_id = 'prod_zemmacos' AND is_active = true");
console.log('Plans:', JSON.stringify(plans.rows));

const otp = await pool.query(
  "SELECT otp_code, expires_at FROM otp_verifications WHERE email = 'test@websmithdigital.com' AND purpose = 'trial_activation' AND verified = FALSE ORDER BY created_at DESC LIMIT 1"
);
console.log('OTP:', JSON.stringify(otp.rows));

const trial = await pool.query(
  "SELECT id, status, expiry_date, license_key FROM trials WHERE customer_email = 'test@websmithdigital.com' ORDER BY created_at DESC LIMIT 1"
);
console.log('Trial:', JSON.stringify(trial.rows));

await pool.end();
