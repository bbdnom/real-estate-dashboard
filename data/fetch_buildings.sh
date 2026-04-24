#!/bin/bash

SERVICE_KEY="9592646786f0e43f7b99248b636bb75cc0880cf2e9c9996bb80d48757671853b"
SIGUNGU="11650"
BJDONG="10100"
BASE_URL="https://apis.data.go.kr/1613000/BldRgstHubService/getBrTitleInfo"

PARCELS=(
  "474-1" "474-2" "474-3" "474-4" "474-5" "474-6" "474-7" "474-8" "474-9"
  "474-13" "474-14" "474-15" "474-17" "474-18" "474-19" "474-20" "474-21" "474-22"
  "474-34" "474-36" "474-37" "474-38"
  "475-1" "475-2" "475-3" "475-4" "475-5" "475-7" "475-8" "475-9"
  "475-11" "475-12" "475-13" "475-14" "475-15" "475-16" "475-17" "475-18" "475-19" "475-20"
  "475-22" "475-26" "475-27" "475-28" "475-29" "475-31"
  "527-7" "527-8" "527-9"
  "528-0" "528-93" "528-94" "528-95" "528-97" "528-98"
  "531-1" "531-7" "531-8" "531-9"
  "980-23" "980-24" "980-25" "980-26" "980-27" "980-54" "980-56"
)

OUTPUT_DIR="/home/hemannkim/real-estate-dashboard/data/raw"
mkdir -p "$OUTPUT_DIR"

for parcel in "${PARCELS[@]}"; do
  IFS='-' read -r bun ji <<< "$parcel"
  bun4=$(printf "%04d" "$bun")
  ji4=$(printf "%04d" "$ji")
  
  URL="${BASE_URL}?serviceKey=${SERVICE_KEY}&sigunguCd=${SIGUNGU}&bjdongCd=${BJDONG}&bun=${bun4}&ji=${ji4}&numOfRows=50&pageNo=1&type=json"
  
  # Use original parcel name (528-0 -> 528)
  display_name="$parcel"
  if [ "$ji" = "0" ]; then
    display_name="$bun"
  fi
  
  echo "Fetching $display_name (bun=$bun4, ji=$ji4)..."
  curl -sk "$URL" -o "$OUTPUT_DIR/${display_name}.json" 2>/dev/null
  sleep 0.3
done

echo "All done. Raw files in $OUTPUT_DIR"
