set -a; source .env; set +a

curl "https://services2.arcgis.com/qvkbeam7Wirps6zC/arcgis/rest/services/RentalStatuses/FeatureServer/0/query?outFields=*&where=1%3D1&f=geojson" > download/rental.geojson

ogr2ogr -f PGDUMP download/rental.sql -lco LAUNDER=NO -lco DROP_TABLE=OFF download/rental.geojson

PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_HOST -p $POSTGRES_PORT -U $POSTGRES_USER -d postgres -a  -f download/rental.sql

rm download/rental.geojson
rm download/rental.sql
