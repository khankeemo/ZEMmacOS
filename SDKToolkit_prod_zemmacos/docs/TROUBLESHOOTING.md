# Troubleshooting

## Common Issues

### "api-config.json not found"
Ensure the `config/` directory with `api-config.json` is inside the SDK folder. This file is generated automatically when you publish your product.

### "Cannot generate hardware fingerprint"
The SDK could not identify stable hardware. Ensure:
- CPU identifier is accessible
- Administrator/root privileges on some systems
- Not running in a restrictive container or sandbox

### License activation fails
- Check internet connectivity
- Verify the license key is correct
- Ensure the license key has not already been activated on another device
- Contact support if the issue persists

### OTP not received
- Check spam/junk folder
- Ensure email address is correct
- Wait a few minutes and try again
- Contact support if the issue persists

### API connection timeout
- Check internet connectivity
- Verify the API URL in `api-config.json`
- Firewall may be blocking outbound connections

### Cache corruption
If the cache becomes corrupted, delete `~/.websmith/<product_id>/` and restart the application. The SDK will re-validate with the server.

### Trial does not start
- OTP must be verified before trial can start
- Ensure all required fields (name, email, mobile) are provided
- Check that hardware fingerprint was generated successfully

### Device replacement fails
- Both old and new hardware must be accessible
- New hardware fingerprint must be generated before replacement
- Internet connection is required

## Security Warnings

- No hardware ID → activation disabled
- Invalid hardware → all license controls disabled
- User closes onboarding → application must close
- Failed OTP → application must block
- Failed trial → application must block
- Invalid license → application must block

## Support

Contact: support@websmithdigital.com
