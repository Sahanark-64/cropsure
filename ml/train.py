"""Train MobileNetV2 from a folder-per-class image dataset."""
import argparse,json
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import tensorflow as tf
from sklearn.metrics import classification_report,ConfusionMatrixDisplay
def main():
 p=argparse.ArgumentParser();p.add_argument('--data',default='dataset');p.add_argument('--validation-data',default=None,help='Separate class-folder validation dataset, stratified by class');p.add_argument('--output',default='saved_models/crop_health.keras');p.add_argument('--epochs',type=int,default=8);p.add_argument('--test-data',default=None,help='Optional separate class-folder test dataset');a=p.parse_args();root=Path(a.data)
 if not root.is_dir() or not any(x.is_dir() for x in root.iterdir()):raise SystemExit('Dataset must contain one subfolder per class, each with images.')
 if a.validation_data:
  train=tf.keras.utils.image_dataset_from_directory(root,image_size=(224,224),batch_size=32,shuffle=True,seed=42);val=tf.keras.utils.image_dataset_from_directory(a.validation_data,image_size=(224,224),batch_size=32,shuffle=False)
  if train.class_names!=val.class_names:raise SystemExit('Validation directory class names/order must match training data.')
 else:
  train=tf.keras.utils.image_dataset_from_directory(root,validation_split=.2,subset='training',seed=42,image_size=(224,224),batch_size=32);val=tf.keras.utils.image_dataset_from_directory(root,validation_split=.2,subset='validation',seed=42,image_size=(224,224),batch_size=32,shuffle=False)
 names=train.class_names
 aug=tf.keras.Sequential([tf.keras.layers.RandomFlip('horizontal'),tf.keras.layers.RandomRotation(.08),tf.keras.layers.RandomZoom(.1)]);base=tf.keras.applications.MobileNetV2(input_shape=(224,224,3),include_top=False,weights='imagenet');base.trainable=False
 inp=tf.keras.Input((224,224,3));x=aug(inp);x=tf.keras.applications.mobilenet_v2.preprocess_input(x);x=base(x,training=False);x=tf.keras.layers.GlobalAveragePooling2D()(x);x=tf.keras.layers.Dropout(.25)(x);out=tf.keras.layers.Dense(len(names),activation='softmax')(x);model=tf.keras.Model(inp,out);model.compile(optimizer='adam',loss='sparse_categorical_crossentropy',metrics=['accuracy']);hist=model.fit(train,validation_data=val,epochs=a.epochs)
 outpath=Path(a.output);outpath.parent.mkdir(parents=True,exist_ok=True);model.save(outpath);outpath.with_suffix('.classes.json').write_text(json.dumps(names,indent=2));y=np.concatenate([y.numpy() for _,y in val]);pred=np.argmax(model.predict(val),axis=1);print('Validation report:');print(classification_report(y,pred,target_names=names,zero_division=0));ConfusionMatrixDisplay.from_predictions(y,pred,display_labels=names,xticks_rotation=45);plt.tight_layout();plt.savefig(outpath.parent/'validation_confusion_matrix.png');plt.figure();plt.plot(hist.history['accuracy'],label='train accuracy');plt.plot(hist.history['val_accuracy'],label='validation accuracy');plt.legend();plt.savefig(outpath.parent/'training_accuracy.png');plt.figure();plt.plot(hist.history['loss'],label='train loss');plt.plot(hist.history['val_loss'],label='validation loss');plt.legend();plt.savefig(outpath.parent/'training_loss.png')
 if a.test_data:
  test=tf.keras.utils.image_dataset_from_directory(a.test_data,shuffle=False,image_size=(224,224),batch_size=32)
  if test.class_names!=names:raise SystemExit('Test directory class names/order must match the training dataset.')
  yt=np.concatenate([labels.numpy() for _,labels in test]);pt=np.argmax(model.predict(test),axis=1);print('Held-out test report:');print(classification_report(yt,pt,target_names=names,zero_division=0));ConfusionMatrixDisplay.from_predictions(yt,pt,display_labels=names,xticks_rotation=45);plt.tight_layout();plt.savefig(outpath.parent/'test_confusion_matrix.png')
if __name__=='__main__':main()
