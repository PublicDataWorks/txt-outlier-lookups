set -a; source .env; set +a

BASE_URL="https://services2.arcgis.com/qvkbeam7Wirps6zC/arcgis/rest/services/RentalStatuses/FeatureServer/0/query"
BATCH_SIZE=1000
START_ID=0
FINAL_GEOJSON="/tmp/rental.geojson"
TEMP_GEOJSON="/tmp/temp_batch.geojson"
FINAL_SQL="/tmp/rental.sql"

while true; do
    END_ID=$((START_ID + BATCH_SIZE))
    echo "Fetching records with ObjectID range: $START_ID to $END_ID"

    curl "${BASE_URL}?outFields=*&where=ObjectID>=${START_ID}+AND+ObjectID<${END_ID}&f=geojson" > "$TEMP_GEOJSON"

    if [ "$(cat $TEMP_GEOJSON)" = '{"type":"FeatureCollection","features":[]}' ]; then
        break
    fi

    if [ "$START_ID" -eq 0 ]; then
        mv "$TEMP_GEOJSON" "$FINAL_GEOJSON"
    else
        jq -s '.[0].features = (.[0].features + .[1].features) | .[0]' "$FINAL_GEOJSON" "$TEMP_GEOJSON" > "$FINAL_GEOJSON.tmp"
        cat "$FINAL_GEOJSON.tmp" > "$FINAL_GEOJSON"
        rm "$FINAL_GEOJSON.tmp"
    fi

    START_ID=$END_ID
    sleep 1
done

ogr2ogr -f PGDUMP $FINAL_SQL -lco LAUNDER=NO -lco DROP_TABLE=OFF "$FINAL_GEOJSON"

psql "$DATABASE_URL" -c "DROP TABLE IF EXISTS public.rental;"

psql "$DATABASE_URL" -a -f "$FINAL_SQL" > /dev/null

psql "$DATABASE_URL" -c "
ALTER TABLE public.rental RENAME TO residential_rental_registrations;
DROP TABLE IF EXISTS address_lookup.residential_rental_registrations;
ALTER TABLE public.residential_rental_registrations SET SCHEMA address_lookup;
"

rm "$FINAL_GEOJSON"
rm "$TEMP_GEOJSON"
rm "$FINAL_SQL"
