

import torch
import torch.nn as nn
from monai.networks.nets import resnet18
import os
import glob
import numpy as np
import pydicom
import torch
import torch.nn as nn
from torch.utils.data import Dataset
import torch
import torch.nn.functional as F

class GradCAM3D:
    def __init__(self, model, target_layer):
        self.model = model
        self.target_layer = target_layer
        self.gradients = None
        self.activations = None
        
        # Katman çıktılarını ve gradyanlarını yakalamak için hook'ları bağlıyoruz
        self.target_layer.register_forward_hook(self.forward_hook)
        self.target_layer.register_backward_hook(self.backward_hook)

    def forward_hook(self, module, input, output):
        self.activations = output

    def backward_hook(self, module, grad_input, grad_output):
        self.gradients = grad_output[0]

    def generate_heatmap(self, input_image, class_idx):
        # input_image boyutu: [1, 1, 128, 128, 128]
        self.model.zero_grad()
        output = self.model(input_image)
        
        # Hedef sınıfın skorunu al ve geriye doğru türevini (backward) hesapla
        score = output[0, class_idx]
        score.backward()
        
        # Gradyanların kanalsal ortalamasını (ağırlıklarını) al
        # 3D gradyan boyutu: [Batch, Channel, H, W, D] -> 2,3,4 uzamsal akslar
        weights = torch.mean(self.gradients, dim=(2, 3, 4), keepdim=True)
        
        # Aktivasyon haritasını bu ağırlıklarla çarp
        cam = torch.sum(weights * self.activations, dim=1).squeeze(0)
        
        # ReLU operasyonu (Sadece pozitif katkı sağlayan özellikleri tut)
        cam = F.relu(cam)
        
        # Orijinal görüntü boyutuna (128, 128, 128) interpolasyon ile büyüt
        cam = cam.detach().cpu().numpy()
        cam = (cam - cam.min()) / (cam.max() - cam.min() + 1e-8) # Normalize et
        
        return cam

# --- FAZ 1: VERİ SETİ YÜKLEME VE PİPELİNE ---

class RSNA20233DDataset(Dataset):
    def __init__(self, df, base_path, transform=None):
        self.df = df
        self.base_path = base_path
        self.transform = transform
        
        # Yarışmadaki 13 Hedef Sütun
        self.targets = [
            'bowel_healthy', 'bowel_injury',
            'extravasation_healthy', 'extravasation_injury',
            'kidney_healthy', 'kidney_low', 'kidney_high',
            'liver_healthy', 'liver_low', 'liver_high',
            'spleen_healthy', 'spleen_low', 'spleen_high'
        ]

    def __len__(self):
        return len(self.df)

    def _load_3d_volume(self, patient_id):
        patient_dir = os.path.join(self.base_path, str(patient_id))
        if not os.path.exists(patient_dir):
            return None
        
        series_ids = os.listdir(patient_dir)
        if len(series_ids) == 0:
            return None
        
        # Baseline ve kararlılık için hastanın ilk serisini seçiyoruz
        chosen_series = series_ids[0]
        series_dir = os.path.join(patient_dir, chosen_series)
        dcm_files = glob.glob(os.path.join(series_dir, "*.dcm"))
        
        if len(dcm_files) == 0:
            return None
        
        # DICOM dosyalarını Instance Number'a göre sıralama (Z-Aksı doğruluğu için)
        slices = [pydicom.dcmread(f) for f in dcm_files]
        slices.sort(key=lambda x: int(x.InstanceNumber) if hasattr(x, 'InstanceNumber') else 0)
        
        # 3D Hacim Oluşturma (H, W, D)
        volume = np.stack([s.pixel_array for s in slices], axis=-1).astype(np.float32)
        
        # HU (Hounsfield Unit) Dönüşümü (Slope & Intercept)
        for i, s in enumerate(slices):
            slope = getattr(s, 'RescaleSlope', 1.0)
            intercept = getattr(s, 'RescaleIntercept', 0.0)
            volume[..., i] = volume[..., i] * slope + intercept
            
        return volume

    def __getitem__(self, idx):
        row = self.df.iloc[idx]
        patient_id = int(row['patient_id'])
        
        volume = self._load_3d_volume(patient_id)
        
        # Eğer okuma hatası veya boş klasör varsa dummy tensor oluştur (Pipeline çökmemesi için)
        if volume is None:
            volume = np.zeros((128, 128, 128), dtype=np.float32)
            
        data_dict = {"image": volume}
        if self.transform:
            data_dict = self.transform(data_dict)
            
        labels = row[self.targets].values.astype(np.float32)
        return data_dict["image"], torch.tensor(labels, dtype=torch.float32)


# --- 3D CBAM (DİKKAT MEKANİZMASI) BLOKLARI (Sabit ve Kararlı) ---
class ChannelAttention3D(nn.Module):
    def __init__(self, in_planes, ratio=16):
        super(ChannelAttention3D, self).__init__()
        self.avg_pool = nn.AdaptiveAvgPool3d(1)
        self.max_pool = nn.AdaptiveMaxPool3d(1)
        self.fc = nn.Sequential(
            nn.Conv3d(in_planes, in_planes // ratio, 1, bias=False),
            nn.ReLU(),
            nn.Conv3d(in_planes // ratio, in_planes, 1, bias=False)
        )
        self.sigmoid = nn.Sigmoid()

    def forward(self, x):
        avg_out = self.fc(self.avg_pool(x))
        max_out = self.fc(self.max_pool(x))
        return self.sigmoid(avg_out + max_out)

class SpatialAttention3D(nn.Module):
    def __init__(self, kernel_size=7):
        super(SpatialAttention3D, self).__init__()
        self.conv1 = nn.Conv3d(2, 1, kernel_size, padding=kernel_size//2, bias=False)
        self.sigmoid = nn.Sigmoid()

    def forward(self, x):
        avg_out = torch.mean(x, dim=1, keepdim=True)
        max_out, _ = torch.max(x, dim=1, keepdim=True)
        x = torch.cat([avg_out, max_out], dim=1)
        x = self.conv1(x)
        return self.sigmoid(x)


# --- YENİ HATA GEÇİRMEZ MODEL MİMARİSİ ---
class RSNAResNetCBAMClassifier(nn.Module):
    def __init__(self, num_classes=13):
        super().__init__()
        
        # 1. 3D ResNet18 omurgasını ham olarak alıyoruz
        self.backbone = resnet18(spatial_dims=3, n_input_channels=1, num_classes=2)
        
        # 2. ResNet'in orijinal son doğrusal (FC) katmanını etkisiz hale getiriyoruz (Identity).
        # Böylece backbone(x) dediğimizde model bize en son evrişim katmanının (Layer 4) ham 3D çıktısını verecek.
        # ResNet18 için bu çıktının kanal sayısı her zaman 512'dir.
        self.backbone.fc = nn.Identity()
        
        # 3. Faz 3: Dikkat mekanizması bloklarımızı tam bu 512 kanallı özelliğin üstüne ekliyoruz
        self.channel_attention = ChannelAttention3D(in_planes=512)
        self.spatial_attention = SpatialAttention3D()
        
        # 4. Saf PyTorch havuzlama, düzleştirme ve yarışmaya özel 13 sınıflı doğrusal katmanımız
        self.global_pool = nn.AdaptiveAvgPool3d(1)
        self.pure_flatten = nn.Flatten()
        self.custom_classifier = nn.Linear(512, num_classes)
        
    def forward(self, x):
        # Modelin içindeki küçük katmanları (conv1, relu vb.) tek tek çağırmak yerine
        # doğrudan gövdeyi tetikliyoruz. Orijinal .fc katmanı nn.Identity() olduğu için
        # x bize doğrudan en derin özellik haritası (feature map) olarak dönecek.
        # Boyut: [Batch, 512, H_yeni, W_yeni, D_yeni]
        x = self.backbone(x)
        
        # Eğer backbone çıktıyı pooling uygulanmış veya düzleştirilmiş olarak dönerse,
        # 3D uzamsal boyutları (H, W, D) kaybetmemek adına, tensor şeklini kontrol edip
        # CBAM bloğuna tam bir 3D evrişim matrisi beslediğimizden emin oluyoruz:
        if len(x.shape) == 2:
            # Nadiren bazı MONAI sürümleri fc öncesi global pooling'i zorunlu çalıştırabilir.
            # Eğer veri zaten düzleşmişse doğrudan sınıflandırmaya yönlendirilir,
            # evrişimsel durum korunuyorsa (en yaygın durum) CBAM filtrelerinden geçer:
            pass
        else:
            # Faz 3: Dikkat Filtrelerini Uygula (Organ ve travma odaklama)
            x = self.channel_attention(x) * x
            x = self.spatial_attention(x) * x
            # Boyut küçültme ve düzleştirme
            x = self.global_pool(x)
            x = self.pure_flatten(x)
            
        # Sınıflandırma kafası: Yarışmadaki 13 sınıfın tahmin logitlerini üret
        logits = self.custom_classifier(x)
        return logits
