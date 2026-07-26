import os
from ultralytics import YOLO

model_rev = 21

# Displaying the parent directory of the script
folder = os.path.dirname(__file__)

# Load a pretrained YOLO26n model
ml_model = YOLO("yolo11n.pt")
output_dir = f"{folder}/compass-model-new"

# Train the model on the COCO8 dataset for 100 epochs
train_results = ml_model.train(
    data=f"compass-detection.v{model_rev}i.yolo11/data.yaml",  # Path to dataset configuration file
    epochs=100,  # Number of training epochs
    imgsz=640,  # Image size for training
    device="cpu",  # Device to run on (e.g., 'cpu', 0, [0,1,2,3])
    save_dir=output_dir,  # Folder to store training data
)

# Evaluate the model's performance on the validation set
metrics = ml_model.val()

# Perform object detection on an image
# results = ml_model("Yolo26/My First Project.v5i.yolo26/Screenshot.jpg")  # Predict on an image
# results[0].show()  # Display results

# Export the model to ONNX format for deployment
path = ml_model.export(format="onnx")  # Returns the path to the exported model

