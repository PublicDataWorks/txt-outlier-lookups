set -a; source .env; set +a
current_date=$(date +%d%m%Y)

PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_HOST -p $POSTGRES_PORT -U $POSTGRES_USER -d postgres -a  -f download/mi_wayne_detroit.sql

PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f download/mi_wayne_detroit.sql -c "
ALTER TABLE address_lookup.mi_wayne_detroit RENAME TO mi_wayne_detroit_${current_date};
ALTER TABLE public.mi_wayne_detroit SET SCHEMA address_lookup;
"

rm download/mi_wayne_detroit.sql
rm download/mi_wayne_detroit.sql.zip
