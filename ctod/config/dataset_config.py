import json
import os
import logging

from ctod.server.queries import QueryParameters


class DatasetConfig:
    """Load and parse dataset configurations from a JSON file."""

    def __init__(self, json_path: str):
        self.datasets = {}
        valid_path = self._validate_path(json_path)
        if valid_path:
            self._load_json(json_path)

    def _validate_path(self, json_path: str) -> bool:
        """
        Validates the given JSON file path.

        Args:
            json_path (str): The path of the JSON file to be validated.

        Returns:
            bool: True if the JSON file path is valid, False otherwise.
        """

        if not os.path.exists(json_path):
            logging.error(f"JSON file not found: {json_path}")
            return False
        if not json_path.endswith('.json'):
            logging.error(f"""Invalid file type: {
                          json_path}. Expected a .json file.""")
            return False

        return True

    def _load_json(self, json_path: str):
        """
        Load JSON file and parse the dataset configurations.

        Args:
            json_path (str): The path to the JSON file.
        """
        try:
            with open(json_path, 'r') as f:
                data = json.load(f)
        except json.JSONDecodeError:
            logging.error(f"Invalid JSON file: {json_path}")
            return

        if not isinstance(data, dict) or 'datasets' not in data:
            logging.error(
                "Invalid JSON file. Expected a dictionary with a 'datasets' key.")
            return

        for dataset in data.get('datasets', []):
            name = dataset.get('name')
            if not name:
                logging.error("Invalid JSON file. Dataset name is required.")
                return

            options = dataset.get('options', {})
            defaultGridSize = options.get('defaultGridSize', None)
            if defaultGridSize is not None:
                defaultGridSize = json.dumps(defaultGridSize)

            zoomGridSizes = options.get('zoomGridSizes', None)
            if zoomGridSizes is not None:
                zoomGridSizes = json.dumps(zoomGridSizes)

            qp = QueryParameters(
                cog=options.get('cog', None),
                minZoom=options.get('minZoom', None),
                maxZoom=options.get('maxZoom', None),
                resamplingMethod=options.get('resamplingMethod', None),
                meshingMethod=options.get('meshingMethod', None),
                skipCache=options.get('skipCache', None),
                defaultGridSize=defaultGridSize,
                zoomGridSizes=zoomGridSizes,
                defaultMaxError=options.get('defaultMaxError', None),
                zoomMaxErrors=options.get('zoomMaxErrors', None),
                extensions=options.get('extensions', None),
                noData=options.get('noData', None),
            )

            self.datasets[name] = qp

    def get_dataset_names(self):
        """
        Returns the names of the datasets.

        Returns:
            list: The names of the datasets.
        """

        return list(self.datasets.keys())

    def get_dataset(self, name: str):
        """
        Retrieves a dataset by its name.

        Parameters:
            name (str): The name of the dataset.

        Returns:
            The dataset query paramaters for the given name, or None if the dataset does not exist.
        """

        if name not in self.datasets:
            return None

        return self.datasets[name]
