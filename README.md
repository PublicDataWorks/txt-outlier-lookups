# txt-outlier-lookup

## Docker Quick Start

```bash
docker build -t lookup .
docker run -p 5000:5000 --name lookup_app --restart unless-stopped lookup
```

## Setup
### Prerequisites

- Python 3.x
- Docker (for containerized deployment)
- Supabase account (for pg_cron extension)

### Cron Job Initialization
The script `scripts/init_cron.py` initializes cron jobs using the [pg_cron extension](https://supabase.com/docs/guides/database/extensions/pg_cron) of Supabase. 
These cron jobs are scheduled to run at 00:00 on the first day of every month.
To initialize the cron jobs, run the following command:

```sh
python -m scripts.init_cron
```
