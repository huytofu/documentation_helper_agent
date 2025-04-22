import torch
import psutil
from dataclasses import dataclass
from typing import Dict, List, Optional

@dataclass
class HardwareSpecs:
    gpu_name: Optional[str] = None
    gpu_memory: Optional[int] = None  # in GB
    gpu_count: int = 0
    cpu_count: int = 0
    total_ram: int = 0  # in GB
    cuda_available: bool = False
    cuda_version: Optional[str] = None
    compute_capability: Optional[float] = None
    is_ampere_or_newer: bool = False
    is_ampere: bool = False
    is_hopper: bool = False
    is_ada_lovelace: bool = False

class HardwareDetector:
    @staticmethod
    def get_hardware_specs() -> HardwareSpecs:
        specs = HardwareSpecs()
        
        # CPU and RAM info
        specs.cpu_count = psutil.cpu_count()
        specs.total_ram = psutil.virtual_memory().total // (1024**3)  # Convert to GB
        
        # GPU info
        specs.cuda_available = torch.cuda.is_available()
        if specs.cuda_available:
            specs.gpu_count = torch.cuda.device_count()
            specs.gpu_name = torch.cuda.get_device_name(0)
            specs.gpu_memory = torch.cuda.get_device_properties(0).total_memory // (1024**3)  # Convert to GB
            specs.cuda_version = torch.version.cuda
            specs.compute_capability = torch.cuda.get_device_capability(0)[0] + torch.cuda.get_device_capability(0)[1] / 10
            
            # Check GPU architecture
            specs.is_ampere_or_newer = specs.compute_capability >= 8.0
            specs.is_ampere = 8.0 <= specs.compute_capability < 9.0
            specs.is_hopper = 9.0 <= specs.compute_capability < 10.0
            specs.is_ada_lovelace = specs.compute_capability >= 10.0
        
        return specs
    
    @staticmethod
    def get_optimization_recommendations(specs: HardwareSpecs) -> Dict[str, List[str]]:
        recommendations = {
            "memory_efficiency": [],
            "parallelism": [],
            "data_optimization": [],
            "computation": []
        }
        
        # Memory Efficiency Recommendations
        if specs.gpu_memory and specs.gpu_memory < 32:
            recommendations["memory_efficiency"].extend([
                "gradient_accumulation",  # High impact, low code changes
                "selective_freezing",     # High impact, low code changes
                "gradient_checkpointing"  # High impact, medium code changes
            ])
        
        # Parallelism Recommendations
        if specs.gpu_count > 1:
            recommendations["parallelism"].extend([
                "tensor_parallel",        # High impact, medium code changes
                "data_parallel",          # High impact, low code changes
                "gradient_sync"           # High impact, low code changes
            ])
        
        # Data Optimization Recommendations
        if specs.total_ram < 64:  # Less than 64GB RAM
            recommendations["data_optimization"].extend([
                "dynamic_batching",       # High impact, low code changes
                "memory_mapping",         # High impact, medium code changes
                "prefetching"             # Medium impact, low code changes
            ])
        
        # Computation Optimization Recommendations
        if specs.is_ampere_or_newer:
            recommendations["computation"].extend([
                "flash_attention",        # High impact, low code changes
                "kernel_fusion",          # High impact, medium code changes
                "mixed_precision"         # High impact, low code changes
            ])
        
        return recommendations
    
    @staticmethod
    def get_optimization_config(specs: HardwareSpecs, recommendations: Dict[str, List[str]]) -> Dict:
        config = {}
        
        # Memory Efficiency Config
        if "gradient_accumulation" in recommendations["memory_efficiency"]:
            config["gradient_accumulation_steps"] = 4
        if "selective_freezing" in recommendations["memory_efficiency"]:
            config["frozen_layers"] = ["embeddings", "layer.0", "layer.1"]
        if "gradient_checkpointing" in recommendations["memory_efficiency"]:
            config["use_gradient_checkpointing"] = True
        
        # Parallelism Config
        if "tensor_parallel" in recommendations["parallelism"]:
            config["tensor_parallel_size"] = min(2, specs.gpu_count)
        if "data_parallel" in recommendations["parallelism"]:
            config["data_parallel_size"] = specs.gpu_count
        if "gradient_sync" in recommendations["parallelism"]:
            config["gradient_sync_frequency"] = 1
        
        # Data Optimization Config
        if "dynamic_batching" in recommendations["data_optimization"]:
            config["max_tokens_per_batch"] = 8192
        if "memory_mapping" in recommendations["data_optimization"]:
            config["use_memory_mapping"] = True
        if "prefetching" in recommendations["data_optimization"]:
            config["prefetch_factor"] = 2
        
        # Computation Optimization Config
        if "flash_attention" in recommendations["computation"]:
            config["use_flash_attention"] = True
        if "kernel_fusion" in recommendations["computation"]:
            config["use_kernel_fusion"] = True
        if "mixed_precision" in recommendations["computation"]:
            config["use_mixed_precision"] = True
        
        return config 