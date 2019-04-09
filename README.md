## SyntaxSQLNet: Syntax Tree Networks for Complex and Cross-Domain Text-to-SQL Task

Source code of our EMNLP 2018 paper: [SyntaxSQLNet: Syntax Tree Networks for Complex and Cross-DomainText-to-SQL Task
](https://arxiv.org/abs/1810.05237).

### Citation

```
@InProceedings{Yu&al.18.emnlp.syntax,
  author =  {Tao Yu and Michihiro Yasunaga and Kai Yang and Rui Zhang and Dongxu Wang and Zifan Li and Dragomir Radev},
  title =   {SyntaxSQLNet: Syntax Tree Networks for Complex and Cross-Domain Text-to-SQL Task},
  year =    {2018},  
  booktitle =   {Proceedings of EMNLP},  
  publisher =   {Association for Computational Linguistics},
}
```

#### Environment Setup

1. The code uses Python 2.7 and [Pytorch 0.2.0](https://pytorch.org/previous-versions/) GPU.
2. Install Python dependency: `pip install -r requirements.txt`

#### Download Data, Embeddings, Scripts, and Pretrained Models
1. Download the dataset from [the Spider task website](https://yale-lily.github.io/spider) to be updated, and put `tables.json`, `train.json`, and `dev.json` under `data/` directory.
2. Download the pretrained [Glove](https://nlp.stanford.edu/data/wordvecs/glove.42B.300d.zip), and put it as `glove/glove.%dB.%dd.txt`
3. Download `evaluation.py` and `process_sql.py` from [the Spider github page](https://github.com/taoyds/spider)
4. Download preprocessed train/dev datasets and pretrained models from [here](https://drive.google.com/file/d/1FHEcceYuf__PLhtD5QzJvexM7SNGnoBu/view?usp=sharing). It contains: 
   -`generated_datasets/`
    - ``generated_data`` for original Spider training datasets, pretrained models can be found at `generated_data/saved_models`
    - ``generated_data_augment`` for original Spider + augmented training datasets, pretrained models can be found at `generated_data_augment/saved_models`

#### Generating Train/dev Data for Modules
You could find preprocessed train/dev data in ``generated_datasets/``.

To generate them by yourself, update dirs under `TODO` in `preprocess_train_dev_data.py`, and run the following command to generate training files for each module:
```
python preprocess_train_dev_data.py train|dev
```

#### Folder/File Description
- ``data/`` contains raw train/dev/test data and table file
- ``generated_datasets/`` described as above
- ``models/`` contains the code for each module.
- ``evaluation.py`` is for evaluation. It uses ``process_sql.py``.
- ``train.py`` is the main file for training. Use ``train_all.sh`` to train all the modules (see below).
- ``test.py`` is the main file for testing. It uses ``supermodel.sh`` to call the trained modules and generate SQL queries. In practice, and use ``test_gen.sh`` to generate SQL queries.
- `generate_wikisql_augment.py` for cross-domain data augmentation


#### Training
Run ``train_all.sh`` to train all the modules.
It looks like:
```
python train.py \
    --data_root       path/to/generated_data \
    --save_dir        path/to/save/trained/module \
    --history_type    full|no \
    --table_type      std|no \
    --train_component <module_name> \
    --epoch           <num_of_epochs>
```

#### Testing
Run ``test_gen.sh`` to generate SQL queries.
``test_gen.sh`` looks like:
```
SAVE_PATH=generated_datasets/generated_data/saved_models_hs=full_tbl=std
python test.py \
    --test_data_path  path/to/raw/test/data \
    --models          path/to/trained/module \
    --output_path     path/to/print/generated/SQL \
    --history_type    full|no \
    --table_type      std|no \
```

#### Evaluation
Follow the general evaluation process in [the Spider github page](https://github.com/taoyds/spider).

#### Cross-Domain Data Augmentation
You could find preprocessed augmented data at `generated_datasets/generated_data_augment`. 

If you would like to run data augmentation by yourself, first download `wikisql_tables.json` and `train_patterns.json` from [here](https://drive.google.com/file/d/13I_EqnAR4v2aE-CWhJ0XQ8c-UlGS9oic/view?usp=sharing), and then run ```python generate_wikisql_augment.py``` to generate more training data. Second, run `get_data_wikisql.py` to generate WikiSQL augment json file. Finally, use `merge_jsons.py` to generate the final spider + wikisql + wikisql augment dataset.

#### Acknowledgement

The implementation is based on [SQLNet](https://github.com/xiaojunxu/SQLNet). Please cite it too if you use this code.
