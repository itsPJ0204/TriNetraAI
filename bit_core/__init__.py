import sys
from bit_core.resnet import resnet18, resnet34, resnet50, resnet101, resnet152
from bit_core import help_funcs
from bit_core import networks

# Alias as models for compatibility with original BIT imports
sys.modules['models'] = sys.modules[__name__]
sys.modules['models.help_funcs'] = help_funcs
sys.modules['models.networks'] = networks
sys.modules['models.resnet'] = sys.modules['bit_core.resnet']
