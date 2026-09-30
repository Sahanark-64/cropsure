import argparse,json
from pathlib import Path
import numpy as np
import tensorflow as tf
p=argparse.ArgumentParser();p.add_argument('image');p.add_argument('--model',default='saved_models/crop_health.keras');a=p.parse_args();path=Path(a.model);model=tf.keras.models.load_model(path);classes=json.loads(path.with_suffix('.classes.json').read_text());image=tf.keras.utils.load_img(a.image,target_size=(224,224));arr=tf.keras.utils.img_to_array(image)[None,...];probs=model.predict(arr,verbose=0)[0];i=int(np.argmax(probs));print(json.dumps({'class':classes[i],'confidence':round(float(probs[i])*100,2)}))
