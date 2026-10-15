import h5py
import json

f = h5py.File("capstone-final/plant_disease.h5", "r")
print("H5 Keys:", list(f.keys()))
print("H5 Attributes:", list(f.attrs.keys()))

if "model_config" in f.attrs:
    config = f.attrs["model_config"]
    if isinstance(config, bytes):
        config = config.decode("utf-8")
    print("\nModel config (first 1000 chars):")
    print(config[:1000])
    
    cfg_json = json.loads(config)
    print("\nModel class:", cfg_json.get("class_name"))
    layers = cfg_json.get("config", {}).get("layers", [])
    print("Num layers:", len(layers))
    for l in layers[:5]:
        print(" Layer:", l.get("class_name"), l.get("config", {}).get("name"))
    print(" ...")
    for l in layers[-5:]:
        print(" Layer:", l.get("class_name"), l.get("config", {}).get("name"))

if "keras_version" in f.attrs:
    print("\nKeras version saved with:", f.attrs["keras_version"])
