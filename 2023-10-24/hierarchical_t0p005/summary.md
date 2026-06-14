# Hierarchical GeoJSON — Classification Summary

- **PSGC version:** `2023-10-24`
- **NAMRIA version:** `2023-11-06`
- **Generated:** 2026-06-14T15:15:08.247559+00:00
- **Total features written:** 47,435
- **Feature conservation:** OK

## Output Files

| Type | File | Features | Exact | HUC map | Fuzzy | Unresolved |
|------|------|---------:|------:|--------:|------:|-----------:|
| Country (ADM0) | `country.geojson` | 3,640 | 3,640 | 0 | 0 | 0 |
| Region | `regions.geojson` | 17 | 17 | 0 | 0 | 0 |
| Province | `provinces.geojson` | 82 | 82 | 0 | 0 | 0 |
| Municipality | `municipalities.geojson` | 1,485 | 1,467 | 0 | 18 | 0 |
| Highly Urbanized City | `highly_urbanized_cities.geojson` | 34 | 31 | 1 | 2 | 0 |
| Independent Component City | `independent_component_cities.geojson` | 6 | 6 | 0 | 0 | 0 |
| Component City | `component_cities.geojson` | 110 | 110 | 0 | 0 | 0 |
| Submunicipality | `submunicipalities.geojson` | 0 | 0 | 0 | 0 | 0 |
| Barangay | `barangays.geojson` | 42,026 | 38,771 | 0 | 3,255 | 0 |
| Special Geographic Area | `special_geographic_areas.geojson` | 9 | 1 | 8 | 0 | 0 |
| Unresolved | `unresolved.geojson` | 6 | 0 | 4 | 0 | 2 |
| Non-administrative | `non_administrative.geojson` | 20 | 0 | 0 | 0 | 0 |

## Count Reconciliation (NAMRIA output vs PSGC reference)

| Type | Actual | Expected | Diff | Tolerance | Status |
|------|-------:|---------:|-----:|----------:|:------:|
| Country (ADM0) | 3,640 | 1 | +3,639 | ±100,000 | ✓ |
| Region | 17 | 17 | +0 | ±0 | ✓ |
| Province | 82 | 82 | +0 | ±0 | ✓ |
| Municipality | 1,485 | 1,485 | +0 | ±2 | ✓ |
| Highly Urbanized City | 34 | 33 | +1 | ±1 | ✓ |
| Independent Component City | 6 | 6 | +0 | ±0 | ✓ |
| Component City | 110 | 111 | -1 | ±1 | ✓ |
| Submunicipality | 0 | 14 | -14 | ±0 | ✗ |
| Barangay | 42,026 | 42,001 | +25 | ±50 | ✓ |
| Special Geographic Area | 9 | 9 | +0 | ±0 | ✓ |

## Coverage Gaps

- **PSGC entities without a NAMRIA polygon:** 230
- **NAMRIA features without a PSGC match:** 6

### PSGC → NAMRIA (entities with no NAMRIA polygon)

| Type | Expected | Matched | Missing |
|------|---------:|--------:|--------:|
| Barangay | 42,001 | 41,803 | 198 |
| Component City | 111 | 110 | 1 |
| Municipality | 1,485 | 1,476 | 9 |
| Special Geographic Area | 9 | 1 | 8 |
| Submunicipality | 14 | 0 | 14 |

<details><summary><b>Barangay</b> — 198 missing</summary>


| PSGC Code | Name |
|-----------|------|
| 0330100012 | Lourdes Sur East |
| 0402103077 | Aniban 2 |
| 0402103079 | Ligas 1 |
| 0402103081 | Maliksi 2 |
| 0402103082 | Mambog 2 |
| 0402103084 | P.F. Espiritu 2 |
| 0402103085 | P.F. Espiritu 4 |
| 0402103086 | Poblacion |
| 0402103088 | Salinas 2 |
| 0402103089 | Sinbanali |
| 0402103090 | Talaba 1 |
| 0402103091 | Talaba 3 |
| 0402103092 | Zapote 1 |
| 0402103093 | Zapote 2 |
| 0631000025 | Buhang Taft North |
| 0631000050 | Dungon A |
| 0631000051 | Dungon B |
| 0631000095 | Lopez Jaena Norte |
| 0631000096 | Lopez Jaena Sur |
| 0631000103 | Magsaysay Village |
| 0631000155 | San Jose |
| 0631000159 | San Pedro |
| 0631000173 | South San Jose |
| 0631000196 | Pale Benedicto Rizal |
| 0631000198 | Luna |
| 0631000199 | San Isidro |
| 0631000200 | San Jose |
| 0631000201 | Tabuc Suba |
| 0730600050 | Pahina Central |
| 0730600063 | Quiot Pardo |
| 0730600068 | San Nicolas Central |
| 0730600086 | To-ong Pardo |
| 0831600013 | Barangay 6-A |
| 0831600022 | Barangay 103-A |
| 0831600043 | Barangay 21-A |
| 0831600058 | Barangay 35-A |
| 0831600061 | Barangay 37-A |
| 0831600068 | Barangay 43-A |
| 0831600069 | Barangay 43-B |
| 0831600071 | Barangay 44-A |
| 0831600078 | Barangay 50-A |
| 0831600079 | Barangay 50-B |
| 0831600090 | Barangay 60-A |
| 0831600097 | Barangay 66-A |
| 0831600116 | Barangay 83-A |
| 0831600135 | Barangay 109-A |
| 0831600137 | Barangay 5-A |
| 0831600138 | Barangay 36-A |
| 0831600139 | Barangay 42-A |
| 0831600140 | Barangay 48-A |
| 0831600141 | Barangay 48-B |
| 0831600142 | Barangay 51-A |
| 0831600143 | Barangay 54-A |
| 0831600145 | Barangay 56-A |
| 0831600146 | Barangay 59-A |
| 0831600147 | Barangay 59-B |
| 0831600148 | Barangay 62-A |
| 0831600149 | Barangay 62-B |
| 0831600150 | Barangay 83-B |
| 0831600151 | Barangay 83-C |
| 0831600152 | Barangay 95-A |
| 0831600153 | Barangay 8-A |
| 0831600154 | Barangay 23-A |
| 0831600155 | Barangay 94-A |
| 0931700028 | Dulian |
| 0931700039 | Latuan |
| 1030900047 | Upper Hinaplanon |
| 1130700036 | Crossing Bayabas |
| 1130700082 | New Carmen |
| 1130700117 | Talomo River |
| 1230800003 | Baluan |
| 1230800004 | Buayan |
| 1230800005 | Bula |
| 1230800006 | Conel |
| 1230800007 | Dadiangas East |
| 1230800009 | Katangawan |
| 1230800011 | Lagao |
| 1230800012 | Labangal |
| 1230800015 | Ligaya |
| 1230800016 | Mabuhay |
| 1230800023 | San Isidro |
| 1230800024 | San Jose |
| 1230800026 | Sinawal |
| 1230800027 | Tambler |
| 1230800028 | Tinagacan |
| 1230800029 | Apopong |
| 1230800030 | Siguel |
| 1230800031 | Upper Labay |
| 1230800032 | Batomelong |
| 1230800033 | Calumpang |
| 1230800034 | City Heights |
| 1230800037 | Dadiangas West |
| 1230800038 | Fatima |
| 1230800039 | Olympog |
| 1380601203 | Barangay 202-A |
| 1380606194 | Barangay 587-A |
| 1380608002 | Barangay 659-A |
| 1380608004 | Barangay 660-A |
| 1380608014 | Barangay 663-A |
| 1380611004 | Barangay 664-A |
| 1380614101 | Barangay 818-A |
| 1380800009 | New Alabang Village |
| 1381300099 | San Isidro Labrador |
| 1381300114 | Silangan |
| 1381300142 | North Fairview |
| 1381500022 | New Lower Bicutan |
| 1381500037 | South Cembo |
| 1381600032 | Wawang Pulo |
| 1430300159 | Magsaysay, Upper |
| 1630400065 | Manila de Bugabus |
| 1731500063 | Inagawan Sub-Colony |
| 1908702003 | Cabayuan |
| 1908702004 | Calaan |
| 1908702006 | Edcor |
| 1908705001 | Ambolodto |
| 1908705002 | Awang |
| 1908705003 | Badak |
| 1908705004 | Bagoenged |
| 1908705005 | Baka |
| 1908705006 | Benolen |
| 1908705007 | Bitu |
| 1908705008 | Bongued |
| 1908709010 | Landasan |
| 1908709011 | Limbayan |
| 1908709024 | Tagudtongan |
| 1908710001 | Alamada |
| 1908710002 | Banatin |
| 1908710003 | Banubo |
| 1908710004 | Bulalo |
| 1908710005 | Bulibod |
| 1908710006 | Calsada |
| 1908801001 | Dicalongan |
| 1908801002 | Kakal |
| 1908802001 | Digal |
| 1908806009 | Katil |
| 1908806014 | Malala |
| 1908806016 | Manindolo |
| 1908806023 | Sepaka |
| 1908807001 | Alonganan |
| 1908807002 | Ambadao |
| 1908807003 | Balanakan |
| 1908807004 | Balong |
| 1908807005 | Buayan |
| 1908807006 | Dado |
| 1908807007 | Damabalas |
| 1908807008 | Duaminanga |
| 1908807009 | Kalipapa |
| 1908807015 | Poblacion |
| 1908809008 | Salbu |
| 1908811001 | Badak |
| 1908811002 | Bulod |
| 1908811003 | Kaladturan |
| 1908811004 | Kulasi |
| 1908811005 | Lao-lao |
| 1908811006 | Lasangan |
| 1908811007 | Lower Idtig |
| 1908811008 | Lumabao |
| 1908811009 | Makainis |
| 1908811011 | Midpandacan |
| 1908813002 | Dabenayan |
| 1908813005 | Liab |
| 1908813007 | Lusay |
| 1908813009 | Manongkaling |
| 1908813010 | Pidsandawan |
| 1908815001 | Balatungkayo |
| 1908815002 | Bulit |
| 1908815003 | Bulod |
| 1908815004 | Dungguan |
| 1908815005 | Limbalud |
| 1908815006 | Maridagao |
| 1908815007 | Nabundas |
| 1908815008 | Pagagawan |
| 1908815009 | Talapas |
| 1908815010 | Talitay |
| 1908815011 | Tunggol |
| 1908816001 | Bagoenged |
| 1908816002 | Buliok |
| 1908816004 | Damalasak |
| 1908820005 | Lapok |
| 1908823010 | Papakan |
| 1908824003 | Boboguiron |
| 1908824004 | Damablac |
| 1908824005 | Fugotan |
| 1908824006 | Fukol |
| 1908824007 | Katibpuan |
| 1908824010 | Linamunan |
| 1999901001 | Kib-Ayao |
| 1999901003 | Langogan |
| 1999901007 | Tupig |
| 1999902001 | Buluan |
| 1999902002 | Nanga-an |
| 1999902003 | Pedtad |
| 1999905001 | Balacayon |
| 1999905005 | Kadingilan |
| 1999905009 | Matilac |
| 1999905010 | Patot |
| 1999906007 | Nunguan |
| 1999907004 | Bulol |

</details>

<details><summary><b>Component City</b> — 1 missing</summary>


| PSGC Code | Name |
|-----------|------|
| 0990101000 | City of Isabela |

</details>

<details><summary><b>Municipality</b> — 9 missing</summary>


| PSGC Code | Name |
|-----------|------|
| 1908705000 | Datu Odin Sinsuat |
| 1908708000 | Northern Kabuntalan |
| 1908710000 | Sultan Kudarat |
| 1908802000 | Buluan |
| 1908807000 | Datu Piang |
| 1908809000 | Datu Saudi Ampatuan |
| 1908811000 | Gen. S.K. Pendatun |
| 1908815000 | Pagagawan |
| 1908824000 | Talayan |

</details>

<details><summary><b>Special Geographic Area</b> — 8 missing</summary>


| PSGC Code | Name |
|-----------|------|
| 1999901000 | Carmen Cluster |
| 1999902000 | Kabacan Cluster |
| 1999903000 | Midsayap Cluster I |
| 1999904000 | Midsayap Cluster II |
| 1999905000 | Pigcawayan Cluster |
| 1999906000 | Pikit Cluster I |
| 1999907000 | Pikit Cluster II |
| 1999908000 | Pikit Cluster III |

</details>

<details><summary><b>Submunicipality</b> — 14 missing</summary>


| PSGC Code | Name |
|-----------|------|
| 1380601000 | Tondo I/II |
| 1380602000 | Binondo |
| 1380603000 | Quiapo |
| 1380604000 | San Nicolas |
| 1380605000 | Santa Cruz |
| 1380606000 | Sampaloc |
| 1380607000 | San Miguel |
| 1380608000 | Ermita |
| 1380609000 | Intramuros |
| 1380610000 | Malate |
| 1380611000 | Paco |
| 1380612000 | Pandacan |
| 1380613000 | Port Area |
| 1380614000 | Santa Ana |

</details>

### NAMRIA → PSGC (features that failed classification)

| Type | ADM Level | Name | NAMRIA PCODE | PSGC Status |
|------|-----------|------|--------------|-------------|
| Mm District | 2 | Metropolitan Manila First District | `PH13039` | non-standard |
| Mm District | 2 | Metropolitan Manila Second District | `PH13074` | non-standard |
| Mm District | 2 | Metropolitan Manila Third District | `PH13075` | non-standard |
| Mm District | 2 | Metropolitan Manila Fourth District | `PH13076` | non-standard |
| Unresolved | 4 | Dadiangas South | `PH1206303036` | unmatched |
| Unresolved | 4 | Pedtad | `PH1909902003` | unmatched |

## Known Limitations

- **Submunicipalities:** NAMRIA ADM4 contains no separate polygons for the 14 Manila submunicipalities (they exist only as barangay parents).
  - Aggregation from barangays is out of scope.

