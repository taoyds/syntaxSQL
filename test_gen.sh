#!/bin/bash

export CUDA_VISIBLE_DEVICES=2,3
TEST_DATA=data/dev.json

# # full + aug
SAVE_PATH=generated_datasets/generated_data_augment/saved_models_hs=full_tbl=std
python test.py \
    --test_data_path  ${TEST_DATA} \
    --models          ${SAVE_PATH} \
    --output_path     ${SAVE_PATH}/dev_result.txt \
    --history_type    full \
    --table_type      std \
     > ${SAVE_PATH}/dev_result.out.txt 2>&1 &


# - aug
SAVE_PATH=generated_datasets/generated_data/saved_models_hs=full_tbl=std
python test.py \
    --test_data_path  ${TEST_DATA} \
    --models          ${SAVE_PATH} \
    --output_path     ${SAVE_PATH}/dev_result.txt \
    --history_type    full \
    --table_type      std \
     > ${SAVE_PATH}/dev_result.out.txt 2>&1 &


# - aug - table
SAVE_PATH=generated_datasets/generated_data/saved_models_hs=full_tbl=no
python test.py \
    --test_data_path  ${TEST_DATA} \
    --models          ${SAVE_PATH} \
    --output_path     ${SAVE_PATH}/dev_result.txt \
    --history_type    full \
    --table_type      no \
     > ${SAVE_PATH}/dev_result.out.txt 2>&1 &


# - aug - table - history
SAVE_PATH=generated_datasets/generated_data/saved_models_hs=no_tbl=no
python test.py \
    --test_data_path  ${TEST_DATA} \
    --models          ${SAVE_PATH} \
    --output_path     ${SAVE_PATH}/dev_result.txt \
    --history_type    no \
    --table_type      no \
     > ${SAVE_PATH}/dev_result.out.txt 2>&1 &
