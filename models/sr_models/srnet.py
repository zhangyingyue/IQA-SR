import torch.nn as nn
import math

from .blocks import Conv3x3, BasicConv, relu

__all__ = ['SRResNet']
__MM__ = 'SRResNet'


class SRResBlock(nn.Module):
    def __init__(self, channels=64):
        super().__init__()
        self.conv1 = Conv3x3(channels, channels, bn=True, act=True)
        self.conv2 = Conv3x3(channels, channels, bn=True, act=False)

    def forward(self, x):
        y = self.conv1(x)
        return self.conv2(y) + x


class SRUpsample(nn.Module):
    def __init__(self, scale=2, in_ch=64):
        super().__init__()
        self.conv = Conv3x3(in_ch, int(in_ch*scale*scale))
        self.up = nn.PixelShuffle(scale)
        self.act = relu()

    def forward(self, x):
        x = self.conv(x)
        return self.act(self.up(x))


class SRResNet(nn.Module):
    def __init__(self, scale=4, colors=3, blocks=16, channels=64):
        super().__init__()
        self.head = BasicConv(colors, channels, 9, bn=False, act=True)

        self.body = nn.Sequential()
        for i in range(blocks):
            self.body.add_module('resblock'+str(i), SRResBlock(channels))

        self.body.add_module('waist', Conv3x3(channels, channels))

        if scale in (2,3):
            up_modules = [SRUpsample(scale, channels)]
        elif scale == 4:
            up_modules = [SRUpsample(2, channels), SRUpsample(2, channels)]
        else:
            raise ValueError('the upsampling rate has to be 2, 3, or 4')
        self.upsample = nn.Sequential(*up_modules)

        self.out = BasicConv(channels, colors, 9)

        self._init_weights()

    def _init_weights(self, part=None):
        module = part if part is not None else self
        for m in module.modules():
            if isinstance(m, nn.Conv2d):
                n = m.kernel_size[0] * m.kernel_size[1] * m.out_channels
                m.weight.data.normal_(0, math.sqrt(2. / n))
            elif isinstance(m, nn.BatchNorm2d):
                m.weight.data.fill_(1)
                m.bias.data.zero_()

    def forward(self, x):
        res = self.head(x)
        x = self.body(res) + res
        x = self.upsample(x)
        x = self.out(x)

        return x
