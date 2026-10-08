# NHS Mental Health & Economic Inactivity Navigator

Free, open-source, patient-facing platform combining NHS Talking Therapies (IAPT)
waiting time data, NHS RTT physical health data, and ONS economic inactivity data
across England's 42 ICB regions — with a 5-question personalised matching engine
that connects waiting patients to the right support organisation for them.

**1.7 million people are on NHS mental health waiting lists. This tool helps them
navigate the system — and shows the economic cost of the backlog.**

## Run it locally
```
pip install -r requirements.txt
streamlit run app.py
```

## Project structure
```
mh-navigator/
├── app.py                          Streamlit app, 5 tabs
├── requirements.txt
├── README.md
├── data/
│   └── organisations.csv           14-organisation matching database
├── scripts/
│   ├── matching_engine.py          5-question filter logic
│   └── download_latest_data.py     monthly NHS data fetcher
└── .github/workflows/
    └── update_data.yml             monthly auto-refresh
```

## The three layers
1. **Navigate** — waiting times by postcode, trust comparison, MH vs physical
   health gap, patient rights guide
2. **Match** — 5-question intake → top 3 matched organisations, with crisis
   fast-track (Samaritans/Shout shown first if urgency = tonight)
3. **Evidence** — ONS economic inactivity connected to waiting time data

## Data
- NHS Talking Therapies (IAPT) monthly statistics — digital.nhs.uk
- NHS RTT waiting times — england.nhs.uk
- ONS economic inactivity by local authority — ons.gov.uk
- Auto-refresh monthly via GitHub Actions (`.github/workflows/update_data.yml`)

*Current build ships with representative demo data; the pipeline swaps in the
live monthly NHS files.*

## Crisis support
Samaritans **116 123** (free, 24/7) · text **SHOUT to 85258** · NHS 111 option 2

Built by Gokul Rajan — gokulrajan.336@gmail.com
