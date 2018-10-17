import json
import torch
import datetime
import argparse
import numpy as np
from utils import *
from word_embedding import WordEmbedding
from models.agg_predictor import AggPredictor
from models.col_predictor import ColPredictor
from models.desasc_limit_predictor import DesAscLimitPredictor
from models.having_predictor import HavingPredictor
from models.keyword_predictor import KeyWordPredictor
from models.multisql_predictor import MultiSqlPredictor
from models.op_predictor import OpPredictor
from models.root_teminal_predictor import RootTeminalPredictor
from models.andor_predictor import AndOrPredictor

TRAIN_COMPONENTS = ('multi_sql','keyword','col','op','agg','root_tem','des_asc','having','andor')
SQL_TOK = ['<UNK>', '<END>', 'WHERE', 'AND', 'EQL', 'GT', 'LT', '<BEG>']
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--toy', action='store_true',
            help='If set, use small data; used for fast debugging.')
    parser.add_argument('--save_dir', type=str, default='',
            help='set model save directory.')
    parser.add_argument('--data_root', type=str, default='',
            help='root path for generated_data')
    parser.add_argument('--train_emb', action='store_true',
            help='Train word embedding.')
    parser.add_argument('--train_component',type=str,default='',
                        help='set train components,available:[multi_sql,keyword,col,op,agg,root_tem,des_asc,having,andor]')
    parser.add_argument('--epoch',type=int,default=500,
                        help='number of epoch for training')
    parser.add_argument('--history_type', type=str, default='full', choices=['full','part','no'], help='full, part, or no history')
    parser.add_argument('--table_type', type=str, default='std', choices=['std','no'], help='standard, hierarchical, or no table info')
    args = parser.parse_args()
    use_hs = True
    if args.history_type == "no":
        args.history_type = "full"
        use_hs = False


    N_word=300
    B_word=42
    N_h = 300
    N_depth=2
    if args.toy:
        USE_SMALL=True
        GPU=True
        BATCH_SIZE=20
    else:
        USE_SMALL=False
        GPU=True
        BATCH_SIZE=64
    # TRAIN_ENTRY=(False, True, False)  # (AGG, SEL, COND)
    # TRAIN_AGG, TRAIN_SEL, TRAIN_COND = TRAIN_ENTRY
    learning_rate = 1e-4
    if args.train_component not in TRAIN_COMPONENTS:
        print("Invalid train component")
        exit(1)
    train_data = load_train_dev_dataset(args.train_component, "train", args.history_type, args.data_root)
    dev_data = load_train_dev_dataset(args.train_component, "dev", args.history_type, args.data_root)
    # sql_data, table_data, val_sql_data, val_table_data, \
    #         test_sql_data, test_table_data, \
    #         TRAIN_DB, DEV_DB, TEST_DB = load_dataset(args.dataset, use_small=USE_SMALL)

    word_emb = load_word_emb('glove/glove.%dB.%dd.txt'%(B_word,N_word), \
            load_used=args.train_emb, use_small=USE_SMALL)
    print("finished load word embedding")
    #word_emb = load_concat_wemb('glove/glove.42B.300d.txt', "/data/projects/paraphrase/generation/para-nmt-50m/data/paragram_sl999_czeng.txt")
    model = None
    if args.train_component == "multi_sql":
        model = MultiSqlPredictor(N_word=N_word,N_h=N_h,N_depth=N_depth,gpu=GPU, use_hs=use_hs)
    elif args.train_component == "keyword":
        model = KeyWordPredictor(N_word=N_word,N_h=N_h,N_depth=N_depth,gpu=GPU, use_hs=use_hs)
    elif args.train_component == "col":
        model = ColPredictor(N_word=N_word,N_h=N_h,N_depth=N_depth,gpu=GPU, use_hs=use_hs)
    elif args.train_component == "op":
        model = OpPredictor(N_word=N_word,N_h=N_h,N_depth=N_depth,gpu=GPU, use_hs=use_hs)
    elif args.train_component == "agg":
        model = AggPredictor(N_word=N_word,N_h=N_h,N_depth=N_depth,gpu=GPU, use_hs=use_hs)
    elif args.train_component == "root_tem":
        model = RootTeminalPredictor(N_word=N_word,N_h=N_h,N_depth=N_depth,gpu=GPU, use_hs=use_hs)
    elif args.train_component == "des_asc":
        model = DesAscLimitPredictor(N_word=N_word,N_h=N_h,N_depth=N_depth,gpu=GPU, use_hs=use_hs)
    elif args.train_component == "having":
        model = HavingPredictor(N_word=N_word,N_h=N_h,N_depth=N_depth,gpu=GPU, use_hs=use_hs)
    elif args.train_component == "andor":
        model = AndOrPredictor(N_word=N_word, N_h=N_h, N_depth=N_depth, gpu=GPU, use_hs=use_hs)
    # model = SQLNet(word_emb, N_word=N_word, gpu=GPU, trainable_emb=args.train_emb)
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate, weight_decay = 0)
    print("finished build model")

    print_flag = False
    embed_layer = WordEmbedding(word_emb, N_word, gpu=GPU,
                                SQL_TOK=SQL_TOK, trainable=args.train_emb)
    print("start training")
    best_acc = 0.0
    for i in range(args.epoch):
        print('Epoch %d @ %s'%(i+1, datetime.datetime.now()))
        print(' Loss = %s'%epoch_train(
                model, optimizer, BATCH_SIZE,args.train_component,embed_layer,train_data,table_type=args.table_type))
        acc = epoch_acc(model, BATCH_SIZE, args.train_component,embed_layer,dev_data,table_type=args.table_type)
        if acc > best_acc:
            best_acc = acc
            print("Save model...")
            torch.save(model.state_dict(), args.save_dir+"/{}_models.dump".format(args.train_component))
