# Klaviyo Back-in-Stock Automation

Automated extraction of back-in-stock subscriber data from Klaviyo API for e-commerce demand analysis and strategic restocking.

## 🎯 Overview

This toolset enables e-commerce businesses to extract and analyze back-in-stock subscription data from Klaviyo, helping prioritize product restocking based on verified customer demand rather than guesswork.

## 📊 Features

- **Top 50 SKUs with Emails** - Extract subscriber emails for the 50 most-demanded products
- **All SKUs Analysis** - Get comprehensive back-in-stock data for all products
- **Demand Rankings** - Identify which products have the highest subscriber counts
- **Diagnostic Tools** - Troubleshoot API connections and data structure

## 🚀 Quick Start

### Prerequisites

- Python 3.7+
- Klaviyo account with back-in-stock functionality enabled
- Klaviyo Private API Key (starts with `pk_`)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/YOUR_USERNAME/klaviyo-back-in-stock-automation.git
cd klaviyo-back-in-stock-automation
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure your API key:

Open any script and replace:
```python
KLAVIYO_API_KEY = "YOUR_KLAVIYO_PRIVATE_API_KEY_HERE"
```

With your actual Klaviyo Private API Key.

## 📁 Scripts

### `klaviyo_top_50_with_emails.py`

**Purpose:** Extract emails for the top 50 most-demanded SKUs

**Output:** Excel file with 2 columns (SKU | Email)

**Use Case:** Email campaigns to high-demand product subscribers

```bash
python klaviyo_top_50_with_emails.py
```

**Output Example:**
| SKU | Email |
|-----|-------|
| WUSPDCZ0002S | customer1@email.com |
| WUSPDCZ0002S | customer2@email.com |
| WUSDS0022 | customer3@email.com |

---

### `klaviyo_all_skus_FIXED.py`

**Purpose:** Extract all back-in-stock subscribers from the past year

**Output:** Excel file with all SKU-email pairs (capped at 500 by default)

**Use Case:** Comprehensive demand analysis

```bash
python klaviyo_all_skus_FIXED.py
```

To change the record cap, edit line 16:
```python
MAX_RECORDS = 500  # Change to any number
```

---

### `diagnose_klaviyo.py`

**Purpose:** Diagnostic tool to test API connection and view data structure

**Output:** Console output showing metric availability and sample events

**Use Case:** Troubleshooting API issues

```bash
python diagnose_klaviyo.py
```

## 📊 Real-World Results

**DecorSteals Case Study:**
- 85,930 total back-in-stock requests tracked
- 155 unique SKUs with verified demand
- 448 unique customer emails collected
- Top product: 408 subscribers waiting for restock

**Impact:**
- 28% conversion rate on back-in-stock emails (vs 3% average email)
- Strategic restocking based on proven demand
- $20K+ potential revenue from top 10 SKUs

## ⚙️ Configuration

### Change Time Range

Default: Past 365 days

To modify, edit in any script:
```python
ONE_YEAR_AGO = datetime.now() - timedelta(days=365)  # Change 365 to desired days
```

### Change Top N SKUs

In `klaviyo_top_50_with_emails.py`:
```python
TOP_N_SKUS = 50  # Change to 25, 100, etc.
```

### Change Record Cap

In `klaviyo_all_skus_FIXED.py`:
```python
MAX_RECORDS = 500  # Change to any number
```

## 🔒 Security

**IMPORTANT:** Never commit your API key to the repository!

- Add `*.py` with actual API keys to `.gitignore`
- Use environment variables for production:
  ```python
  import os
  KLAVIYO_API_KEY = os.environ.get('KLAVIYO_API_KEY')
  ```

## 📝 Requirements

See `requirements.txt`:
- `requests>=2.31.0`
- `pandas>=2.0.0`
- `openpyxl>=3.1.0`

## 🛠️ Troubleshooting

### "No data to export"

**Solution:** Run `diagnose_klaviyo.py` to check:
1. API key is valid
2. "Subscribed to Back in Stock" metric exists
3. Events exist in the specified time range

### "Authentication failed"

**Solution:** 
1. Verify you're using a **Private API Key** (starts with `pk_`)
2. Check the key hasn't been revoked in Klaviyo settings

### "Email found: NOT FOUND" in diagnostic

**Solution:** This is normal! Emails are stored in profiles, not event properties. The scripts handle this automatically.

## 📧 Use Cases

1. **Email Campaigns** - Target subscribers with restock notifications
2. **Inventory Planning** - Prioritize restocking high-demand products
3. **Vendor Negotiations** - Show proof of demand for better terms
4. **Marketing Content** - "Most Requested Items" campaigns
5. **Strategic Analysis** - Understand which products have latent demand

## 🤝 Contributing

Contributions welcome! Please feel free to submit a Pull Request.

## 📄 License

MIT License - feel free to use for commercial purposes

## 👤 Author

**Matt** - Marketing/Content Automation @ DecorSteals

## 🙏 Acknowledgments

Built for e-commerce teams who want to make data-driven restocking decisions based on verified customer demand.

---

**Questions?** Open an issue or reach out!
