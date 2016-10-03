#!/bin/bash
if [ -z "$STOQS_HOME" ]; then
  echo "Set STOQS_HOME variable first, e.g. STOQS_HOME=/opt/stoqsgit_dj1.8" 
  exit 1
fi
if [ -z "$DATABASE_URL" ]; then
  echo "Set DATABASE_URL variable first"
  exit 1
fi
cd "$STOQS_HOME/venv-stoqs/bin"
source activate
cd "$STOQS_HOME/stoqs/loaders/CANON/toNetCDF"
start_datetime='20160101T000000'
end_datetime='20161231T000000'
urlbase='http://elvis.shore.mbari.org/thredds/catalog/LRAUV'
dir='/mbari/LRAUV'
logdir='missionlogs/2016'
search="${logdir}/.*nc4$"
declare -a platforms=("tethys" "makai" "daphne")

while getopts "s:e:" opt; do
    case "$opt" in
    s)  start_datetime="$OPTARG"
        ;;
    e)  end_datetime="$OPTARG"
        ;;
    esac
done
parms_sci="{
            \"CTD_NeilBrown\": [
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
            ]
        }"

parms_eng="{
            \"PNI_TCM\": [
            { \"name\": \"platform_roll_angle\", \"rename\":\"roll\", \"units\":\"degree\" },
            { \"name\": \"platform_pitch_angle\", \"rename\":\"pitch\", \"units\":\"degree\" },
            { \"name\": \"platform_orientation\", \"rename\":\"yaw\", \"units\":\"degree\", \"standard_name\": \"platform_yaw_angle\" }
            ],
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
            \"AHRS_sp3003D\": [
            { \"name\": \"platform_orientation\", \"rename\":\"yaw\" },
            { \"name\": \"platform_pitch_angle\", \"rename\":\"pitch\" },
            { \"name\": \"platform_roll_angle\", \"rename\":\"roll\" }
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


for platform in "${platforms[@]}"
do
        python makeLRAUVNetCDFs.py -u ${urlbase}/${platform}/${search} -i ${dir}/${platform}/${logdir} -p "${parms_sci}" --resampleFreq '10S' -a 'sci' --start "${start_datetime}" --end "${end_datetime}"
        python makeLRAUVNetCDFs.py -u ${urlbase}/${platform}/${search} -i ${dir}/${platform}/${logdir} -p "${parms_eng}" --resampleFreq '2S' -a 'eng' --start "${start_datetime}" --end "${end_datetime}"
done

