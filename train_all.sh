#!/bin/bash

# ## full + aug
# hs=full
# tbl=std
# d_type="_augment"

# ## - aug
hs=full
tbl=std
d_type=""

## - aug - table
# hs=full
# tbl=no
# d_type=""

# ## - aug - table -history
# hs=no
# tbl=no
# d_type=""


# toy="--toy"
toy=""
# epoch=1 # 600 for spider, 200 for +aug

DATE=`date '+%Y-%m-%d-%H:%M:%S'`

data_root=generated_datasets/generated_data${d_type}
save_dir="${data_root}/saved_models_hs=${hs}_tbl=${tbl}_${DATE}"
log_dir=${save_dir}/train_log
mkdir -p ${save_dir}
mkdir -p ${log_dir}


export CUDA_VISIBLE_DEVICES=2
module=col
epoch=600
python train.py \
  --data_root    ${data_root} \
  --save_dir     ${save_dir} \
  --history_type ${hs} \
  --table_type   ${tbl} \
  --train_component ${module} \
  --epoch        ${epoch} \
  ${toy} \
  > "${log_dir}/train_${d_type}_hs=${hs}_tbl=${tbl}_${module}_${DATE}.txt" \
  2>&1 &

export CUDA_VISIBLE_DEVICES=3
epoch=300
for module in multi_sql keyword op agg root_tem des_asc having andor
do
  python train.py \
    --data_root    ${data_root} \
    --save_dir     ${save_dir} \
    --history_type ${hs} \
    --table_type   ${tbl} \
    --train_component ${module} \
    --epoch        ${epoch} \
    ${toy} \
    > "${log_dir}/train_${d_type}_hs=${hs}_tbl=${tbl}_${module}_${DATE}.txt" \
    2>&1 &
done
