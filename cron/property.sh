cd "$(dirname "$0")/.."
set -a; source .env; set +a

current_date=$(date +%d%m%Y)

psql "$DATABASE_URL" -c "DROP TABLE IF EXISTS public.mi_wayne_detroit;"

psql "$DATABASE_URL" -a  -f /tmp/mi_wayne_detroit.sql > /dev/null

psql "$DATABASE_URL" -c "
DROP TABLE IF EXISTS address_lookup.mi_wayne_detroit;
CREATE TABLE address_lookup.mi_wayne_detroit (LIKE public.mi_wayne_detroit INCLUDING ALL);
INSERT INTO address_lookup.mi_wayne_detroit SELECT * FROM public.mi_wayne_detroit;
DROP TABLE IF EXISTS public.mi_wayne_detroit CASCADE;
"

rm /tmp/mi_wayne_detroit.sql
rm /tmp/mi_wayne_detroit.sql.zip
