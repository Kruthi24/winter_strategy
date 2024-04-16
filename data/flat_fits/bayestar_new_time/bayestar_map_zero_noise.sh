#! usr/bin/bash

for DIST in 50 100 150 200; do
    lalapps_inspinj \
    `# Write output to inj.xml.` \
    -o inj.xml \
    `# Mass distribution.` \
    `# In this example, the masses are pinned to 1.4 and 1.4 Msun.` \
    --m-distr fixMasses --fixed-mass1 1.4 --fixed-mass2 1.4 \
    `# Coalescence time distribution: adjust time step, start, and stop time to control the number of injections.` \
    --gps-start-time 1383977402 \
    --gps-end-time 1383977403 \
    --t-distr fixed --time-step 100 \
    `# Distance distribution: uniform in Euclidean volume.` \
    `# WARNING: distances are in kpc.` \
    --d-distr uniform --min-distance $((DIST * 1000)) --max-distance $((DIST * 1000)) \
    `# Sky position and inclination distribution.` \
    --l-distr fixed --longitude -87.85234195489255 --latitude 35.308376046435775 \
    `# --l-distr random `\
    `# Write a table of CBC injections to inj.xml.` \
    --f-lower 40 \
    --disable-spin \
    --polarization 0 \
    --waveform IMRPhenomPv2 \
    --coa-phase-distr fixed --fixed-coa-phase 0 \
    --i-distr fixed --fixed-inc 0 \

    # echo "Waveform Generated"

    # bayestar-sample-model-psd \
    # `# Write output to psd.xml.` \
    # -o psd.xml \
    # --df 0.0125 \
    # --f-max 2048 \
    # `# Specify noise models for desired detectors.` \
    # --H1=aLIGO140MpcT1800545 \
    # --L1=aLIGO140MpcT1800545 \
    # --V1=AdVO3LowT1800545 \


    # echo "PSD Generated"

    echo "running matched filtering"

    bayestar-realize-coincs \
    `# Write output to coinc.xml.` \
    -o coinc.xml \
    `# Use the injections and noise PSDs that we generated.` \
    inj.xml --reference-psd psd.xml \
    `# Specify which detectors are in science mode.` \
    --detector H1 L1 V1 \
    --f-low 40 \
    --f-high 2048 \
    --waveform IMRPhenomPv2 \
    `# Optionally, add Gaussian noise (rather than zero noise).` \
    --measurement-error zero-noise \
    `# Optionally, adjust the detection threshold: single-detector` \
    `# SNR, network SNR, and minimum number of detectors above` \
    `# threshold to form a coincidence.` \
    --snr-threshold 2 \
    --net-snr-threshold 7.0 \
    --min-triggers 2 \
    `# Optionally, save triggers that were below the single-detector` \
    `# threshold.` \
    --keep-subthreshold


    # Explicitly set the number of OpenMP threads
    # instead of using all available cores.

    export OMP_NUM_THREADS=4

    # Run BAYESTAR on all coincident events in coinc.xml.
    echo "Running bayestar"

    bayestar-localize-coincs \
    coinc.xml \
    --f-low 40 \
    --waveform IMRPhenomPv2 \
    --f-high-truncate 0.9999



    echo "Analyzing Map"

    for i in *.fits; do
        [ -f "$i" ] || break
        echo "$i"
        ligo-skymap-plot $i -o "bns_"$DIST"Mpc.png" --annotate --contour 50 90
        ligo-skymap-flatten $i "bns_"$DIST"Mpc_data_flattened.fits"
        gzip "bns_"$DIST"Mpc_data_flattened.fits"
        rm $i
    done
done
