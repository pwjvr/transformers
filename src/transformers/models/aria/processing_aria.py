#                🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨
#           This file was automatically generated from src/transformers/models/aria/modular_aria.py.
#               Do NOT edit this file manually as any edits will be overwritten by the generation of
#             the file from the modular. If any change should be done, please apply the change to the
#                          modular_aria.py file directly. One of our CI enforces this.
#                🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨
import inspect
import re
from typing import List, Optional, Union

import torch
from PIL import Image
from torchvision import transforms

from ...feature_extraction_utils import BatchFeature
from ...image_processing_utils import BaseImageProcessor
from ...image_utils import ImageInput
from ...processing_utils import ProcessorMixin
from ...tokenization_utils import (
    PaddingStrategy,
    PreTokenizedInput,
    TensorType,
    TextInput,
    TruncationStrategy,
)
from ...utils import logging
from ..auto import AutoTokenizer
from .processing_utils import (
    get_split_image,
    keep_ratio_resize_and_pixel_mask,
)


logger = logging.get_logger(__name__)

class AriaVisionProcessor(BaseImageProcessor):
    """
    A vision processor for the Aria model that handles image preprocessing.
    """

    def __init__(
        self,
        max_image_size=980,
        min_image_size=336,
        image_mean=None,
        image_std=None,
        **kwargs,
    ):
        """
        Initialize the AriaVisionProcessor.

        Args:
            max_image_size (int, optional): Maximum image size. Defaults to 980.
            min_image_size (int, optional): Minimum image size. Defaults to 336.
            mean (list, optional): Mean values for normalization. Defaults to [0.5, 0.5, 0.5].
            std (list, optional): Standard deviation values for normalization. Defaults to [0.5, 0.5, 0.5].
        """
        super().__init__(**kwargs)

        if image_mean is None:
            image_mean = [0.5, 0.5, 0.5]
        if image_std is None:
            image_std = [0.5, 0.5, 0.5]
        self.max_image_size = max_image_size
        self.min_image_size = min_image_size
        self.image_mean = image_mean
        self.image_std = image_std
        self.auto_map = {
            "AutoProcessor": "processing_aria.AriaProcessor",
            "AutoImageProcessor": "vision_processor.AriaVisionProcessor",
        }

        # we make the transform a property so that it is lazily initialized,
        # this could avoid the error "TypeError: Object of type Normalize is not JSON serializable"
        # when we used save_pretrained or from_pretrained.
        self._transform = None
        self._set_processor_class("AriaProcessor")

    @property
    def transform(self):
        if self._transform is None:
            # Recreate the transform when accessed
            self._transform = transforms.Compose(
                [
                    transforms.ToTensor(),
                    transforms.Normalize(self.image_mean, self.image_std),
                ]
            )
        return self._transform

    def __call__(
        self,
        images: Union[Image.Image, List[Image.Image]],
        max_image_size: Optional[int] = 980,
        min_image_size: Optional[int] = 336,
        return_tensors: Optional[Union[str, TensorType]] = "pt",
        split_image: Optional[bool] = False,
        split_ratio: Optional[List[List[int]]] = None,
    ):
        """
        Process a list of images.

        Args:
            images (list): List of PIL.Image objects.
            max_image_size (int, optional): Override the default max image size. Defaults to None.
            return_tensors (str or TensorType, optional): The type of tensor to return. Defaults to "pt".
            split_image (bool, optional): Whether to split the image. Defaults to False.
            split_ratio (list, optional): The ratio for splitting the image. Defaults to a list of common split ratios.
        Returns:
            BatchFeature: A BatchFeature object containing:
                - 'pixel_values': Tensor of processed image pixel values.
                - 'pixel_mask': Boolean pixel mask. This mask is a 2D tensor of shape (max_size, max_size) where:
                    - True (1) values indicate pixels that belong to the original resized image.
                    - False (0) values indicate pixels that are part of the padding.
                  The mask helps distinguish between actual image content and padded areas in subsequent processing steps.
                - 'num_crops': Tensor of the number of crops for each image.
        """
        if split_ratio is None:
            split_ratio = [
                [1, 2],
                [1, 3],
                [1, 4],
                [1, 5],
                [1, 6],
                [1, 7],
                [1, 8],
                [2, 4],
                [2, 3],
                [2, 2],
                [2, 1],
                [3, 1],
                [3, 2],
                [4, 1],
                [4, 2],
                [5, 1],
                [6, 1],
                [7, 1],
                [8, 1],
            ]
        max_size = self.max_image_size if max_image_size is None else max_image_size
        min_size = self.min_image_size if min_image_size is None else min_image_size

        if max_size not in [490, 980]:
            raise ValueError("max_image_size must be either 490 or 980")

        if isinstance(images, Image.Image):
            images = [images]

        pixel_values = []
        pixel_masks = []
        num_crops = []

        for image in images:
            crop_images = get_split_image(image, split_image, split_ratio, max_size)
            num_crops.append(torch.tensor(len(crop_images)))
            for crop_image in crop_images:
                img_padded, pixel_mask = keep_ratio_resize_and_pixel_mask(crop_image, max_size, min_size)
                img_padded = self.transform(img_padded)
                pixel_values.append(img_padded)
                pixel_masks.append(pixel_mask)

        return BatchFeature(
            data={
                "pixel_values": torch.stack(pixel_values),
                "pixel_mask": torch.stack(pixel_masks),
                "num_crops": torch.stack(num_crops),
            },
            tensor_type=return_tensors,
        )

    def preprocess(
        self,
        images,
        max_image_size=None,
        min_image_size=None,
        return_tensors: Optional[Union[str, TensorType]] = None,
        split_image: Optional[bool] = False,
        split_ratio: Optional[List[List[int]]] = None,
    ):
        if split_ratio is None:
            split_ratio = [
                [1, 2],
                [1, 3],
                [1, 4],
                [1, 5],
                [1, 6],
                [1, 7],
                [1, 8],
                [2, 4],
                [2, 3],
                [2, 2],
                [2, 1],
                [3, 1],
                [3, 2],
                [4, 1],
                [4, 2],
                [5, 1],
                [6, 1],
                [7, 1],
                [8, 1],
            ]
        return self.__call__(
            images,
            max_image_size=max_image_size,
            min_image_size=min_image_size,
            return_tensors=return_tensors,
            split_image=split_image,
            split_ratio=split_ratio,
        )


class AriaProcessor(ProcessorMixin):
    """
    AriaProcessor is a processor for the Aria model which wraps the Aria image preprocessor and the LLama slow tokenizer.
    Args:
        image_processor(AriaVisionProcessor): The AriaVisionProcessor to use for image preprocessing.
        tokenizer(AutoTokenizer): The AutoTokenizer to use for tokenizing the text.
        patch_size(int): The patch size to use for the image processor.
        chat_template(str): The chat template to use for the tokenizer.
        image_token(str): The image token to use for the tokenizer.
    """

    attributes = []
    valid_kwargs = ["chat_template", "patch_size", "image_token"]
    image_processor_class = None
    tokenizer_class = "AutoTokenizer"

    def __init__(
        self,
        image_processor: AriaVisionProcessor = None,
        tokenizer: Union[AutoTokenizer, str] = None,
        patch_size: int = 490,
        chat_template: str = None,
        image_token: str = "<|img|>",
    ):
        super().__init__(chat_template=chat_template)

        if image_processor is None:
            self.image_processor = AriaVisionProcessor(max_image_size=patch_size)
        else:
            self.image_processor = image_processor

        if isinstance(tokenizer, str):
            self.tokenizer = AutoTokenizer.from_pretrained(tokenizer, trust_remote_code=True, use_fast=False)
        else:
            self.tokenizer = tokenizer

        if self.tokenizer is not None and self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.unk_token

        self.image_token = image_token

    # Copied from models.llava_next.processing_llave_next.LlavaNextProcessor.__call__
    def __call__(
        self,
        text: Union[TextInput, PreTokenizedInput, List[TextInput], List[PreTokenizedInput]],
        images: ImageInput = None,
        padding: Union[bool, str, PaddingStrategy] = False,
        truncation: Union[bool, str, TruncationStrategy] = None,
        max_length: Optional[int] = None,
        max_image_size: Optional[int] = 980,
        split_image: Optional[bool] = False,
        return_tensors: Optional[Union[str, TensorType]] = TensorType.PYTORCH,
    ) -> BatchFeature:
        """
        Main method to prepare for the model one or several sequences(s) and image(s). Please refer to the doctsring
        of the above two methods for more information.

        Args:
            text (`str`, `List[str]`, `List[List[str]]`):
                The sequence or batch of sequences to be encoded. Each sequence can be a string or a list of strings
                (pretokenized string). If the sequences are provided as list of strings (pretokenized), you must set
                `is_split_into_words=True` (to lift the ambiguity with a batch of sequences).
            images (`PIL.Image.Image`, `np.ndarray`, `torch.Tensor`, `List[PIL.Image.Image]`, `List[np.ndarray]`, `List[torch.Tensor]`):
                The image or batch of images to be prepared. Each image can be a PIL image, NumPy array or PyTorch
                tensor. Both channels-first and channels-last formats are supported.
            padding (`bool`, `str` or [`~utils.PaddingStrategy`], *optional*, defaults to `False`):
                Select a strategy to pad the returned sequences (according to the model's padding side and padding
                index) among:
                - `True` or `'longest'`: Pad to the longest sequence in the batch (or no padding if only a single
                  sequence if provided).
                - `'max_length'`: Pad to a maximum length specified with the argument `max_length` or to the maximum
                  acceptable input length for the model if that argument is not provided.
                - `False` or `'do_not_pad'` (default): No padding (i.e., can output a batch with sequences of different
                  lengths).
            max_length (`int`, *optional*):
                Maximum length of the returned list and optionally padding length (see above).
            max_image_size (`int`, *optional*):
                Maximum size of the image to be processed.
            split_image (`bool`, *optional*):
                Whether to split the image into patches before processing.
            truncation (`bool`, *optional*):
                Activates truncation to cut input sequences longer than `max_length` to `max_length`.
            return_tensors (`str` or [`~utils.TensorType`], *optional*):
                If set, will return tensors of a particular framework. Acceptable values are:

                - `'tf'`: Return TensorFlow `tf.constant` objects.
                - `'pt'`: Return PyTorch `torch.Tensor` objects.
                - `'np'`: Return NumPy `np.ndarray` objects.
                - `'jax'`: Return JAX `jnp.ndarray` objects.

        Returns:
            [`BatchFeature`]: A [`BatchFeature`] with the following fields:

            - **input_ids** -- List of token ids to be fed to a model. Returned when `text` is not `None`.
            - **attention_mask** -- List of indices specifying which tokens should be attended to by the model (when
              `return_attention_mask=True` or if *"attention_mask"* is in `self.model_input_names` and if `text` is not
              `None`).
            - **pixel_values** -- Pixel values to be fed to a model. Returned when `images` is not `None`.
            - **pixel_mask** -- Pixel mask to be fed to a model. Returned when `images` is not `None`.
        """
        if isinstance(text, str):
            text = [text]
        elif not isinstance(text, list) and not isinstance(text[0], str):
            raise ValueError("Invalid input text. Please provide a string, or a list of strings")

        if images is not None:
            image_inputs = self.image_processor(
                images,
                return_tensors=return_tensors,
                max_image_size=max_image_size,
                split_image=split_image,
            )
            # expand the image_token according to the num_crops of image
            prompt_strings = []
            crop_iter = iter(image_inputs.pop("num_crops"))
            for prompt in text:
                prompt_strings.append(
                    re.sub(
                        re.escape(self.image_token),
                        lambda _: next(crop_iter) * self.image_token,
                        prompt,
                    )
                )

        else:
            image_inputs = {}
            prompt_strings = text

        text_inputs = self.tokenizer(
            prompt_strings,
            return_tensors=return_tensors,
            padding=padding,
            truncation=truncation,
            max_length=max_length,
        )

        return BatchFeature(data={**text_inputs, **image_inputs})

    @staticmethod
    def _extract_kwargs(func: callable, **kwargs) -> dict:
        """
        Extract the kwargs that are valid for the given function.
        """
        return {k: v for k, v in kwargs.items() if k in inspect.signature(func).parameters}

    def save_pretrained(self, save_directory, **kwargs):
        """
        Save both the image processor and tokenizer.
        """
        if self.image_processor is not None:
            self.image_processor.save_pretrained(
                save_directory,
                **self._extract_kwargs(self.image_processor.save_pretrained, **kwargs),
            )
        if self.tokenizer is not None:
            self.tokenizer.save_pretrained(
                save_directory,
                **self._extract_kwargs(self.tokenizer.save_pretrained, **kwargs),
            )

    @classmethod
    def from_pretrained(
        cls,
        pretrained_model_name_or_path,
        tokenizer_path=None,
        image_processor_path=None,
        **kwargs,
    ):
        """
        Load both the image processor and tokenizer from a pretrained model path.
        """
        tokenizer_path = tokenizer_path if tokenizer_path is not None else pretrained_model_name_or_path
        image_processor_path = (
            image_processor_path if image_processor_path is not None else pretrained_model_name_or_path
        )
        image_processor = AriaVisionProcessor.from_pretrained(
            image_processor_path,
            **cls._extract_kwargs(AriaVisionProcessor.from_pretrained, **kwargs),
        )
        if "use_fast" in kwargs:
            logger.warning("use_fast is not supported for AriaProcessor. Ignoring...")
            kwargs.pop("use_fast")
        try:
            tokenizer = AutoTokenizer.from_pretrained(
                tokenizer_path,
                use_fast=False,
                **cls._extract_kwargs(AutoTokenizer.from_pretrained, **kwargs),
            )
            chat_template = tokenizer.chat_template
        except Exception as e:
            logger.warning(f"Failed to load tokenizer from {tokenizer_path}: {e}")
            tokenizer = None
            chat_template = None
        return cls(
            image_processor=image_processor,
            tokenizer=tokenizer,
            chat_template=chat_template,
        )

    # Copied from transformers.models.clip.processing_clip.CLIPProcessor.batch_decode with CLIP->Llama
    def batch_decode(self, *args, **kwargs):
        """
        This method forwards all its arguments to LlamaTokenizerFast's [`~PreTrainedTokenizer.batch_decode`]. Please
        refer to the docstring of this method for more information.
        """
        return self.tokenizer.batch_decode(*args, **kwargs)

    # Copied from transformers.models.clip.processing_clip.CLIPProcessor.decode with CLIP->Llama
    def decode(self, *args, **kwargs):
        """
        This method forwards all its arguments to LlamaTokenizerFast's [`~PreTrainedTokenizer.decode`]. Please refer to
        the docstring of this method for more information.
        """
        return self.tokenizer.decode(*args, **kwargs)

    @property
    # Copied from transformers.models.clip.processing_clip.CLIPProcessor.model_input_names
    def model_input_names(self):
        tokenizer_input_names = self.tokenizer.model_input_names
        image_processor_input_names = self.image_processor.model_input_names
        return list(dict.fromkeys(tokenizer_input_names + image_processor_input_names))
