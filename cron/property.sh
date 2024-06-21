cd "$(dirname "$0")/.."
set -a; source .env; set +a

current_date=$(date +%d%m%Y)

psql $DATABASE_URL -a  -f /tmp/mi_wayne_detroit.sql

#psql $DATABASE_URL -c "
#ALTER TABLE address_lookup.mi_wayne_detroit RENAME TO mi_wayne_detroit_${current_date};
#ALTER TABLE public.mi_wayne_detroit SET SCHEMA address_lookup;
#"

rm /tmp/mi_wayne_detroit.sql
rm /tmp/download/mi_wayne_detroit.sql.zip
