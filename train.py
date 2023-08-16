import torch
import pytorch_lightning as pl
from pytorch_lightning.callbacks import EarlyStopping

import sys
import warnings
import pandas as pd
from argparse import ArgumentParser
from models.crnn import CRNN
from models.ctc_baseline import CTCBaseline
from data_loader import get_data, IMG_WIDTH, IMG_HEIGHT, HandWritttenDataset
from config import NUM_CLASSES
from predict import predict
from utils import initilize_parameters


def parse_arguments(argv):
    parser = ArgumentParser()
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--val_check_interval', type=float, default=0.25)
    parser.add_argument('--model_name', type=str)

    # Optimization hyperparameters
    parser.add_argument('--epochs', type=int, default=10)
    parser.add_argument('--batch_size', type=int, default=128)
    parser.add_argument('--lr', type=float, default=1e-3)
    parser.add_argument('--momentum', type=float, default=0.9)
    parser.add_argument('--optimizer', type=str, default='adam')
    parser.add_argument('--weight_decay', type=float, default=1e-4)
    parser.add_argument('--dropout', type=float, default=0.5)

    # Learning rate scheduler
    parser.add_argument('--warmup_steps', type=int, default=0)


    # Decode hyperparameters
    parser.add_argument('--decode_method', type=str, default='beam_search')
    parser.add_argument('--beam_size', type=int, default=3)

    return parser.parse_args(argv)


def crnn(args):
    train_loader, val_loader, test_loader = get_data(args.batch_size, args.seed)

    pl.seed_everything(args.seed)

    # model
    crnn = CRNN(3, IMG_HEIGHT, IMG_WIDTH, NUM_CLASSES)
    crnn = initilize_parameters(crnn)
    plcrnn = CTCBaseline(crnn, args)

    early_stop_callback = EarlyStopping(
        monitor='val_loss',
        mode='min', patience=10, verbose=True
    )
    # train model
    trainer = pl.Trainer(
        default_root_dir=f'checkpoints/{args.model_name}/',
        max_epochs=args.epochs,
        val_check_interval=args.val_check_interval,
    )
    trainer.fit(
        model=plcrnn, train_dataloaders=train_loader, val_dataloaders=val_loader
    )

    # Save models
    torch.save(plcrnn.model.state_dict(), f'saved_models/{args.model_name}.pt')

    print('Predicting...')
    print('-' * 50)

    label2char = HandWritttenDataset.LABEL2CHAR
    preds, img_names = predict(plcrnn, test_loader, label2char, args.decode_method, args.beam_size)

    df = pd.DataFrame({'file_name': img_names, 'pred': preds})
    df.to_csv(f'predictions/{args.model_name}.txt', index=False, header=False, sep='\t')


if __name__ == '__main__':
    warnings.filterwarnings('ignore')
    args = parse_arguments(sys.argv[1:])
    crnn(args)