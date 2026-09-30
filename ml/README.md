# Model training

# Train and connect the crop classifier

Install Python 3.11 for the TensorFlow workflow (the live demo backend can run on Python 3.14 without TensorFlow). From the repository root in PowerShell:

    py -3.11 -m venv .venv-ml
    .\.venv-ml\Scripts\Activate.ps1
    python -m pip install -r backend/requirements.txt
    python -m pip install -r ml/requirements.txt

Download and arrange the public PlantVillage data into crop/disease class folders:

    cd ml
    python download_dataset.py

This downloads an approximately 828 MiB CC0 archive. If automated downloads are denied, download the archive from https://data.mendeley.com/datasets/tywbtsjrjv/1 in a browser and run python download_dataset.py --archive downloads/PlantVillage.zip. The script verifies the ZIP, excludes the background-only class, and writes dataset_manifest.csv.

Arrange data as one folder per exact class label. The common PlantVillage convention is Crop___Disease_Name; for example:

    ml/dataset/
      Tomato___Early_blight/
      Tomato___Late_blight/
      Tomato___healthy/
      Potato___Early_blight/
      Potato___Late_blight/
      Potato___healthy/

Use a legally obtained dataset with labels checked by an agricultural expert. Each class needs enough varied images to reserve examples for evaluation. Avoid augmented copies or photos of the same leaf crossing between training and test sets.

From the ml folder, train:

    python train.py --data dataset --output saved_models/crop_health.keras --epochs 8

The script trains MobileNetV2 with an 80/20 training/validation split. It writes the model and its exact class-name list, validation classification report, confusion matrix, accuracy graph, and loss graph. For an independent test, arrange a separate directory with the same class folder names, then run:

    python train.py --data dataset --test-data field_test --output saved_models/crop_health.keras --epochs 8

The held-out report is the more useful estimate of performance on unseen images. For realistic checks, make the test images new field photos from different plants, farms, phones, lighting, and locations. Overall accuracy can hide a weak disease class; review per-class precision/recall and the confusion matrix.

Connect the trained model by copying backend/.env.example to backend/.env and setting:

    MODEL_PATH=../ml/saved_models/crop_health.keras
    AI_REVIEW_THRESHOLD=75

The API loads this Keras model and the sibling crop_health.classes.json file when a photo is uploaded. Restart the backend with the same Python 3.11 environment where TensorFlow was installed. Without MODEL_PATH, the API intentionally stays in mock/demo mode. With it configured, a missing or invalid model returns an API error instead of silently pretending to perform real inference.

The API restricts PlantVillage-style Crop___Disease output classes to the crop selected on the farmer's farm. Classification confidence is the model's score, not a guarantee that its answer is correct. A model trained only on clean, posed leaf images can fail on field backgrounds, mixed symptoms, early infection, or different varieties. Add expert-confirmed local field examples and evaluate on separate local field photos before relying on results. Keep low-confidence cases in expert review and treat every result as a suggestion, not a confirmed diagnosis.

TensorFlow's official install guide lists Python versions and platform-specific wheels; choose a supported Python release. Native-Windows GPU support ended after TensorFlow 2.10, though CPU wheels are available: https://www.tensorflow.org/install/pip
