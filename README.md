# outlier-experiments

## Setup

The script `scripts/init_cron.py` initializes cron jobs using the [pg_cron extension](https://supabase.com/docs/guides/database/extensions/pg_cron) of Supabase. 
These cron jobs are scheduled to run at 00:00 on the first day of every month.
To initialize the cron jobs, run the following command:

```sh
python -m scripts.init_cron
```
