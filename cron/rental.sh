set -a; source .env; set +a

curl "https://services2.arcgis.com/qvkbeam7Wirps6zC/arcgis/rest/services/RentalStatuses/FeatureServer/0/query?outFields=*&where=1%3D1&f=geojson" > /tmp/rental.geojson
ogr2ogr -f PGDUMP /tmp/rental.sql -lco LAUNDER=NO -lco DROP_TABLE=OFF /tmp/rental.geojson

psql $DATABASE_URL -a -f /tmp/rental.sql

rm /tmp/rental.geojson
rm /tmp/rental.sql
