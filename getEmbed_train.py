
# coding: utf-8

# In[213]:

import os

import torch
import torch.nn.functional as F
import torch.nn as nn

from torch import optim
from torch.autograd import Variable

import torchvision
import torchvision.datasets as dset
import torchvision.models as models
import torchvision.transforms as transforms
import torchvision.utils
from torch.utils.data import DataLoader,Dataset
import albumentations
from albumentations import torch as AT

import matplotlib.pyplot as plt

import pandas as pd
import numpy as np

import random
import cv2
from PIL import Image
import PIL.ImageOps    
import pickle


# ## EembeddingNet ResNet50

# In[5]:


class EmbeddingNet(nn.Module):
    
    def __init__(self):
        super(EmbeddingNet, self).__init__()
        resnet = models.resnet50(pretrained=True)
        
        self.model = nn.Sequential(resnet.conv1, resnet.bn1,resnet.relu, resnet.maxpool,resnet.layer1,resnet.layer2,resnet.layer3,resnet.layer4,resnet.avgpool)#,resnet.fc)
        # Fix blocks
        fixed_blocks = 1
        for p in self.model[0].parameters(): p.requires_grad=False
        for p in self.model[1].parameters(): p.requires_grad=False
        if fixed_blocks >= 3:
            for p in self.model[6].parameters(): p.requires_grad=False
        if fixed_blocks >= 2:
            for p in self.model[5].parameters(): p.requires_grad=False
        if fixed_blocks >= 1:
            for p in self.model[4].parameters(): p.requires_grad=False

        def set_bn_fix(m):
            classname = m.__class__.__name__
            if classname.find('BatchNorm') != -1:
                for p in m.parameters(): p.requires_grad=False

        self.model.apply(set_bn_fix)
        
        resnet.fc = nn.Linear(2048, 512, bias=True)
        self.last_layer = resnet.fc
        

    def forward(self, x):    
        x = self.model(x)
        x = x.view(-1, 2048)
        return self.last_layer(x)


# # Get the best model

# In[214]:


siamese_net = torch.load("best_net.pth")
state_dict = siamese_net.state_dict()
embed_net = EmbeddingNet().cuda()
temp_dict = {}
for key in state_dict.keys():
    if key.startswith("embedding_net"):
        temp_dict[key[14:len(key)]] = state_dict[key]
embed_net.load_state_dict(temp_dict)


# In[215]:


class EmbedDataset(Dataset):
    
    def __init__(self,datafolder, df, bbox_df, datatype='train', transform = None):
        self.datafolder = datafolder
        self.df = df
        self.bbox_df = bbox_df
        self.datatype = datatype
        self.transform = transform
        
    def __getitem__(self,idx):
        
        img_idx = idx
    
        img_path = self.df.loc[img_idx,'Image']
        
        bbox = bbox_df.loc[bbox_df.Image==img_path,:].values[0,1:]

        img_pil = Image.open(os.path.join(self.datafolder, img_path)).crop(bbox).convert('RGB')
  
        img = np.array(img_pil)
   
        image = self.transform(image=img)['image']
     
        return image
    
    
    def __len__(self):
        return(self.df.shape[0])


# In[216]:


train_full = pd.read_csv("train.csv")

test_df = pd.read_csv("sample_submission.csv")


bbox_df = pd.read_csv("bounding_boxes.csv")
RESIZE_H = 224
RESIZE_W = 224

data_transforms_test = albumentations.Compose([
    albumentations.Resize(RESIZE_H, RESIZE_W),
    albumentations.Normalize(),
    AT.ToTensor()
])


# In[217]:


train_eb_dataset = EmbedDataset(datafolder="train/", 
                                 df=train_full, bbox_df=bbox_df, datatype='train', transform = data_transforms_test)

train_eb_dataloader = DataLoader(train_eb_dataset,
                        shuffle=True,
                        num_workers=0,
                        batch_size=1)


# In[205]:


embed_net.eval()
df = pd.DataFrame(columns = ["Image", "Id", "Embedding"])
with torch.no_grad():
    for i,data in enumerate(train_eb_dataloader):
       # print(i)
        train_eb_img = data
        train_eb_img = train_eb_img.cuda()
        vector = embed_net(train_eb_img)
        df = df.append({'Image': train_full.loc[i,'Image'], 'Id':  train_full.loc[i,'Id'], 'Embedding':vector}, ignore_index = True)
        print(i)
f =open("train_full_embed.p",'wb')
pickle.dump(df,f)    
#print("the train_full_embed is ok")
p1 = open("train_full_embed.p",'rb')
pp1 = pickle.load(p1)
print("the train_full_embed is ok")










