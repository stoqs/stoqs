#!/bin/bash
# Script executed from cron. Need to occasionally tag the mbari/stoqs image with the image name used in the crontab, e.g.:
# docker tag mbari/stoqs:latest docker_stoqs_lrauv

if [ -z "$STOQS_HOME" ]; then
  echo "Set STOQS_HOME variable first, e.g. STOQS_HOME=/src/stoqsgit"
  exit 1
fi
if [ -z "$DATABASE_URL" ]; then
  echo "Set DATABASE_URL variable first"
  exit 1
fi
cd "$STOQS_HOME/stoqs/loaders/CANON/toNetCDF"
start_datetime='20170101T000000'
end_datetime='20171231T000000'
urlbase='http://elvis.shore.mbari.org/thredds/catalog/LRAUV'
dir='/mbari/LRAUV'
year='2018'
declare -a platforms=("ahi" "aku" "brezo" "daphne" "galene" "makai" "opah" "pontus" "tethys" "triton" "whoidhs")

while getopts "s:e:y:" opt; do
    case "$opt" in
    s)  start_datetime="$OPTARG"
        ;;
    e)  end_datetime="$OPTARG"
        ;;
    y)  year="$OPTARG"
        ;;
    esac
done

logdir="missionlogs/${year}"
search="${logdir}/.*nc4$"

parms_sci="{
            \"CTD_Seabird\": [
            { \"name\":\"sea_water_salinity\" , \"rename\":\"salinity\" },
            { \"name\":\"sea_water_temperature\" , \"rename\":\"temperature\" }
            ],
            \"CTD_NeilBrown\": [ \
            { \"name\":\"sea_water_salinity\" , \"rename\":\"salinity\" },
            { \"name\":\"sea_water_temperature\" , \"rename\":\"temperature\" }
            ],
            \"WetLabsBB2FL\": [  \
            { \"name\":\"mass_concentration_of_chlorophyll_in_sea_water\", \"rename\":\"chlorophyll\" },
            { \"name\":\"Output470\", \"rename\":\"bbp470\" },
            { \"name\":\"Output650\", \"rename\":\"bbp650\" }
            ],
            \"PAR_Licor\": [
            { \"name\":\"downwelling_photosynthetic_photon_flux_in_sea_water\", \"rename\":\"PAR\" }
            ],
            \"ISUS\" : [
            { \"name\":\"mole_concentration_of_nitrate_in_sea_water\", \"rename\":\"nitrate\" }
            ],
            \"Aanderaa_O2\": [
            { \"name\":\"mass_concentration_of_oxygen_in_sea_water\", \"rename\":\"oxygen\" }
            ],
            \"WetLabsSeaOWL_UV_A\": [
            { \"name\":\"concentration_of_chromophoric_dissolved_organic_matter_in_sea_water\", \"rename\":\"chromophoric_dissolved_organic_matter\" },
            { \"name\":\"mass_concentration_of_chlorophyll_in_sea_water\", \"rename\":\"chlorophyll\" },
            { \"name\":\"BackscatteringCoeff700nm\", \"rename\":\"BackscatteringCoeff700nm\" },
            { \"name\":\"VolumeScatCoeff117deg700nm\", \"rename\":\"VolumeScatCoeff117deg700nm\" },
            { \"name\":\"mass_concentration_of_petroleum_hydrocarbons_in_sea_water\", \"rename\":\"petroleum_hydrocarbons\" }
            ]
        }"

parms_eng="{
            \"ElevatorServo\": [
            { \"name\": \"platform_elevator_angle\", \"rename\":\"control_inputs_elevator_angle\" }
            ],
            \"RudderServo\": [
            { \"name\": \"platform_rudder_angle\", \"rename\":\"control_inputs_rudder_angle\" }
            ],
            \"MassServo\": [
            { \"name\": \"platform_mass_position\", \"rename\":\"control_inputs_mass_position\" }
            ],
            \"BuoyancyServo\": [
            { \"name\": \"platform_buoyancy_position\", \"rename\":\"control_inputs_buoyancy_position\" }
            ],
            \"ThrusterServo\": [
            { \"name\": \"platform_propeller_rotation_rate\", \"rename\":\"control_inputs_propeller_rotation_rate\" }
            ],
            \"BPC1\": [
            { \"name\": \"platform_battery_charge\", \"rename\":\"health_platform_battery_charge\" },
            { \"name\": \"platform_battery_voltage\" , \"rename\":\"health_platform_average_voltage\" }
            ],
            \"Onboard\": [
            { \"name\": \"platform_average_current\" , \"rename\":\"health_platform_average_current\" }
            ],
            \"NAL9602\": [
            { \"name\": \"time_fix\" , \"rename\":\"fix_time\" },
            { \"name\": \"latitude_fix\" , \"rename\":\"fix_latitude\" },
            { \"name\": \"longitude_fix\" , \"rename\":\"fix_longitude\" }
            ],
            \"DeadReckonUsingSpeedCalculator\": [
            { \"name\": \"fix_residual_percent_distance_traveled\" , \"rename\":\"fix_residual_percent_distance_traveled_DeadReckonUsingSpeedCalculator\" },
            { \"name\": \"longitude\" , \"rename\":\"pose_longitude_DeadReckonUsingSpeedCalculator\" },
            { \"name\": \"latitude\" , \"rename\":\"pose_latitude_DeadReckonUsingSpeedCalculator\" },
            { \"name\": \"depth\" , \"rename\":\"pose_depth_DeadReckonUsingSpeedCalculator\" }
            ],
            \"DeadReckonUsingMultipleVelocitySources\": [
            { \"name\": \"fix_residual_percent_distance_traveled\" , \"rename\":\"fix_residual_percent_distance_traveled_DeadReckonUsingMultipleVelocitySources\" },
            { \"name\": \"longitude\" , \"rename\":\"pose_longitude_DeadReckonUsingMultipleVelocitySources\" },
            { \"name\": \"latitude\" , \"rename\":\"pose_latitude_DeadReckonUsingMultipleVelocitySources\" },
            { \"name\": \"depth\" , \"rename\":\"pose_depth_DeadReckonUsingMultipleVelocitySources\" }
            ]
        }"

# Remove the first and last characters from parms so that we can combine them
sci_vars=`echo $parms_sci | cut -c 2- | rev | cut -c 2- | rev` 
eng_vars=`echo $parms_eng | cut -c 2- | rev | cut -c 2- | rev` 
parms_scieng="{$sci_vars, $eng_vars}"

for platform in "${platforms[@]}"
do
        python makeLRAUVNetCDFs.py -u ${urlbase}/${platform}/${search} -i ${dir}/${platform}/${logdir} -p "${parms_scieng}" --resampleFreq '2S' -a 'scieng' --start "${start_datetime}" --end "${end_datetime}" --trackingdb --nudge
        python makeLRAUVNetCDFs.py -u ${urlbase}/${platform}/${search} -i ${dir}/${platform}/${logdir} -p "${parms_sci}" --resampleFreq '10S' -a 'sci' --start "${start_datetime}" --end "${end_datetime}" --trackingdb --nudge
        python makeLRAUVNetCDFs.py -u ${urlbase}/${platform}/${search} -i ${dir}/${platform}/${logdir} -p "${parms_eng}" --resampleFreq '2S' -a 'eng' --start "${start_datetime}" --end "${end_datetime}" --trackingdb --nudge
done

