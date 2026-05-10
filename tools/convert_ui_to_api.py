"""
Experimental diagnostic converter.
Do not rely on this for production workflows.
For production, always export workflows from ComfyUI using Save (API Format).
"""
import json
import sys
import os

def convert_ui_to_api(ui_json_path, api_json_path):
    with open(ui_json_path, 'r', encoding='utf-8') as f:
        ui_data = json.load(f)

    nodes = ui_data.get("nodes", [])
    links = ui_data.get("links", [])
    
    # Map link_id to [origin_node_id, origin_slot_index]
    link_map = {}
    for link in links:
        # link format: [id, origin_node, origin_slot, target_node, target_slot, type]
        if len(link) >= 4:
            link_map[link[0]] = [str(link[1]), link[2]]

    api_format = {}

    for node in nodes:
        node_id = str(node["id"])
        class_type = node["type"]
        
        # Skip notes
        if class_type == "MarkdownNote":
            continue

        inputs = {}
        
        # 1. Process widgets_values
        # This is tricky because UI format is a list, API format is a dict.
        # We try to match them based on the 'inputs' and 'properties' or just guess.
        widgets_values = node.get("widgets_values", [])
        
        # For common nodes, we know the keys.
        if class_type == "LoadImage":
            if len(widgets_values) > 0:
                inputs["image"] = widgets_values[0]
        elif class_type == "SaveVideo":
            if len(widgets_values) > 0:
                inputs["filenames_prefix"] = widgets_values[0]
        elif class_type == "PrimitiveNode":
            if len(widgets_values) > 0:
                inputs["value"] = widgets_values[0]
        else:
            # Fallback for custom nodes: try to map by index if possible,
            # but usually it's better to use the 'inputs' list if they are widgets.
            ui_inputs = node.get("inputs", [])
            widget_idx = 0
            
            # This is a heuristic: widgets that aren't linked usually take values from widgets_values
            # Actually, ComfyUI UI format stores widget values in order of the widgets defined in the class.
            # We don't have the class definition, so we just store them as 'widget_0', 'widget_1' if we don't know.
            # BUT, we can check the 'inputs' list in the UI JSON.
            
            for i, val in enumerate(widgets_values):
                inputs[f"widget_{i}"] = val

        # 2. Process links
        ui_inputs = node.get("inputs", [])
        for ui_input in ui_inputs:
            input_name = ui_input["name"]
            link_id = ui_input.get("link")
            if link_id in link_map:
                inputs[input_name] = link_map[link_id]

        api_format[node_id] = {
            "class_type": class_type,
            "inputs": inputs
        }

    # Second pass: fix known node input keys based on common patterns
    for node_id, node_data in api_format.items():
        if node_data["class_type"] == "b94257db-cdc1-45d3-8913-ca61e782d9c1": # LTX Video Gen
            # Based on the UI JSON:
            # 0: Prompt, 1: disable_i2v, 2: width, 3: height, 4: length, ...
            inputs = node_data["inputs"]
            if "widget_0" in inputs: inputs["prompt"] = inputs.pop("widget_0")
            if "widget_1" in inputs: inputs["disable_i2v"] = inputs.pop("widget_1")
            if "widget_2" in inputs: inputs["width"] = inputs.pop("widget_2")
            if "widget_3" in inputs: inputs["height"] = inputs.pop("widget_3")
            if "widget_4" in inputs: inputs["length"] = inputs.pop("widget_4")
            if "widget_5" in inputs: inputs["lora_name"] = inputs.pop("widget_5")
            if "widget_6" in inputs: inputs["model_name"] = inputs.pop("widget_6")
            # ... and so on

    with open(api_json_path, 'w', encoding='utf-8') as f:
        json.dump(api_format, f, indent=2)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python convert_ui_to_api.py <ui_json> <api_json>")
    else:
        convert_ui_to_api(sys.argv[1], sys.argv[2])
