# limitations under the License.
"""Model classes for MetricX, modified from the T5 versions in HF."""

from typing import Dict, List
from .base_metric import BaseMetric

import dataclasses
import json
import os

import datasets
from .utils.metricx import *
import torch
import transformers

class MetricXMetric(BaseMetric):
    """
        args:
            metric_args (Dict): a dictionary of metric arguments
    """
    def __init__(self, metric_args:Dict):
        self.metric_args = metric_args

        self.reference_free = self.metric_args["is_qe"]
        self.tokenizer = transformers.AutoTokenizer.from_pretrained(self.metric_args["tokenizer_name"])
        self.model = MT5ForRegression.from_pretrained(self.metric_args["model_name"])

        if torch.cuda.is_available():
            device = torch.device("cuda")
            self.per_device_batch_size = self.metric_args["batch_size"] // torch.cuda.device_count()
        else:
            device = torch.device("cpu")
            self.per_device_batch_size = self.metric_args["batch_size"]

        self.model.to(device)
        self.model.eval()

        self.training_args = transformers.TrainingArguments(
            per_device_eval_batch_size=self.per_device_batch_size,
            dataloader_pin_memory=False,
        )

        self.trainer = transformers.Trainer(
            model=self.model,
            args=self.training_args,
        )

    def get_dataset(self, input_file: str, tokenizer, max_input_length: int, device, is_qe: bool):
        """Gets the test dataset for prediction.

        If `is_qe` is true, the input data must have "hypothesis" and "source" fields.
        If it is false, there must be "hypothesis" and "reference" fields.

        Args:
            input_file: The path to the jsonl input file.
            tokenizer: The tokenizer to use.
            max_input_length: The maximum input sequence length.
            device: The ID of the device to put the PyTorch tensors on.
            is_qe: Indicates whether the metric is a QE metric or not.

        Returns:
            The dataset.
        """

        def _make_input(example):
            if is_qe:
                example["input"] = (
                    "candidate: "
                    + example["hypothesis"]
                    + " source: "
                    + example["source"]
                )
            else:
                example["input"] = (
                    "candidate: "
                    + example["hypothesis"]
                    + " reference: "
                    + example["reference"]
                )
            return example

        def _tokenize(example):
            return tokenizer(
                example["input"],
                max_length=max_input_length,
                truncation=True,
                padding=False,
            )

        def _remove_eos(example):
            example["input_ids"] = example["input_ids"][:-1]
            example["attention_mask"] = example["attention_mask"][:-1]
            return example

        ds = datasets.load_dataset("json", data_files={"test": input_file})
        ds = ds.map(_make_input)
        ds = ds.map(_tokenize)
        ds = ds.map(_remove_eos)
        ds.set_format(
            type="torch",
            columns=["input_ids", "attention_mask"],
            device=device,
            output_all_columns=True,
        )
        return ds

    def score(self, predictions:List[str], references:List[List[str]]) -> List[float]:
        
        ds = self.get_dataset(
            args.input_file,
            tokenizer,
            args.max_input_length,
            device,
            args.qe,
        )
  
        predictions, _, _ = trainer.predict(test_dataset=ds["test"])


        with open(args.output_file, "w") as out:
            for pred, example in zip(predictions, ds["test"]):
            example["prediction"] = float(pred)
            del example["input"]
            del example["input_ids"]
            del example["attention_mask"]
            out.write(json.dumps(example) + "\n")


        
