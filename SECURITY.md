#  Security Policy

##  Our Commitment

At **ssecgroup**, we take security seriously. This tool is designed for **legitimate business intelligence and educational purposes only**. We are committed to ensuring the security of our users and the platforms we interact with.

##  Responsible Use Warning

This tool interacts with Google Maps, which has its own Terms of Service. Users are **solely responsible** for ensuring their use complies with:

- Google's Terms of Service
- Local laws and regulations
- Robots.txt directives
- Rate limiting guidelines
- Ethical scraping practices

**We do not condone:**
-  Aggressive scraping that disrupts services
-  Violation of Terms of Service
-  Harassment or spam
-  Illegal data collection
-  Any malicious use

##  Reporting a Vulnerability

If you discover a security vulnerability in this project, **please do NOT open a public issue**.

###  Contact Method

**Email:** [ssecgroup@proton.me](mailto:ssecgroup@proton.me)  
**PGP Key:** [Download PGP Key](https://github.com/ssecgroup/pgp-key.asc)  
**ETH for responsible disclosure:** `0x8242f0f25c5445F7822e80d3C9615e57586c6639`

###  What to Include

Please provide:
1. Description of the vulnerability
2. Steps to reproduce
3. Potential impact
4. Suggested fix (if any)
5. Your contact information (optional)

###  Response Timeline

| Timeframe | Action |
|-----------|--------|
| **24-48 hours** | Initial acknowledgment |
| **5-7 days** | Investigation & validation |
| **14 days** | Fix development (if accepted) |
| **30 days** | Public disclosure after fix |

##  Supported Versions

| Version | Supported | Status |
|---------|-----------|--------|
| 5.0.x | ✅ | Current stable |
| 4.x | ⚠️ | Limited support |
| < 4.0 | ❌ | End of life |

##  Security Features

### Built-in Protections

```
┌─────────────────────────────────────┐
│  ✅ Rate limiting (configurable)    │
│  ✅ Request jitter                   │
│  ✅ Consecutive request detection    │
│  ✅ Automatic long breaks             │
│  ✅ Session persistence               │
│  ✅ Cookie management                 │
│  ✅ Error recovery                    │
│  ✅ Graceful shutdown                  │
└─────────────────────────────────────┘
```

### Data Safety

- **Zero data leakage** - All data stays local
- **No telemetry** - We don't track usage
- **No API keys required** - Works out of box
- **Encryption ready** - Use with encrypted drives
- **Checkpoint system** - Prevents data loss

##  Ethical Guidelines

###  Allowed Use Cases
- Market research
- Business intelligence
- Academic research
- Personal projects
- Lead generation (ethical)

###  Prohibited Use Cases
- Spamming businesses
- Harassment
- Competitive sabotage
- Illegal activities
- Terms of Service violation

##  Configuration Security

### Recommended Settings

```json
{
  "rate_limiting": {
    "min_delay": 2,
    "max_delay": 5,
    "jitter": true
  },
  "proxy_rotation": {
    "enabled": false  // Enable only with ethical proxies
  }
}
```

### Security Best Practices

1. **Use VPN/Proxy responsibly** - Only with permission
2. **Respect robots.txt** - Check before scraping
3. **Implement delays** - Don't hammer servers
4. **Monitor logs** - Watch for unusual patterns
5. **Update regularly** - Stay current with fixes

##  Disclosure Policy

We follow **Coordinated Vulnerability Disclosure**:

1. Reporter contacts us privately
2. We validate the issue
3. We develop a fix
4. We release fix with credits (optional)
5. Public disclosure after 30 days

##  Third-Party Dependencies

We regularly audit dependencies for vulnerabilities:

| Tool | Purpose | Security Status |
|------|---------|-----------------|
| Selenium | Browser automation | ✅ Safe |
| ChromeDriver | Driver management | ✅ Safe |
| Pandas | Data processing | ✅ Safe |
| Requests | HTTP client | ✅ Safe |

##  Contact

**Security Team:** [ssecgroup@proton.me](mailto:ssecgroup@proton.me)  
**GitHub:** [@ssecgroup](https://github.com/ssecgroup)  
**ETH (donations/responsible disclosure):** `0x8242f0f25c5445F7822e80d3C9615e57586c6639`

##  Disclaimer

**THIS SOFTWARE IS PROVIDED "AS IS" WITHOUT WARRANTY OF ANY KIND.** The authors and contributors are not responsible for any misuse, damages, or legal issues arising from the use of this software. Users are solely responsible for compliance with all applicable laws and regulations.

---

**Last updated:** February 2026  
**Version:** 5.0.0

*Together, let's build a safer scraping ecosystem.*
