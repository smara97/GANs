import torch
import torchvision
import torch.nn as nn
import torch.optim as optim
import torchvision.datasets as datasets
import torchvision.transforms as transforms

from torch.utils.data import DataLoader
from torch.utils.tensorboard import SummaryWriter

class Discriminator(nn.Module):
    def __init__(self, in_features, hidden_dim) -> None:
        super().__init__()

        self.disc = nn.Sequential(
            nn.Linear(in_features, hidden_dim),
            nn.LeakyReLU(0.1),
            nn.Linear(hidden_dim, 1),
            nn.Sigmoid(),
        )

    def forward(self, x):
        return self.disc(x)
    

class Generator(nn.Module):
    def __init__(self, z_dim, hidden_dim, img_dim) -> None:
        super().__init__()
        self.gen = nn.Sequential(
            nn.Linear(z_dim, hidden_dim),
            nn.LeakyReLU(0.1),
            nn.Linear(hidden_dim, img_dim),
            nn.Tanh()
        )

    def forward(self, x):
        return self.gen(x)
    

# Hyperparameters etc.
device = 'cuda' if torch.cuda.is_available()  else 'cpu'
lr = 3e-4 # Is the best learning rate for Adam Andrej Karapthy
hidden_dim_disc = 128
hidden_dim_gen = 256
z_dim = 64
image_dim = 28*28*1
batch_size = 32
epochs = 50

disc = Discriminator(image_dim, hidden_dim_disc).to(device)
gen = Generator(z_dim, hidden_dim_gen, image_dim).to(device)
fixed_noise = torch.randn((batch_size, z_dim)).to(device)

transforms = transforms.Compose(
    [transforms.ToTensor(), transforms.Normalize((0.1307, ), (0.3081, ))]
)

dataset = datasets.MNIST(root='datasets/', transform=transforms, download=True)
loader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

opt_disc = optim.Adam(disc.parameters(), lr=lr)
opt_gen = optim.Adam(gen.parameters(), lr=lr)

criterion = nn.BCELoss()

writer_fake = SummaryWriter("runs/GAN_MNIST/fake")
writer_real = SummaryWriter("runs/GAN_MNIST/real")

step = 0

for epoch in range(epochs):
    for batch_idx, (real, _) in enumerate(loader):
        real = real.view(-1, 28*28).to(device)
        batch_size = real.shape[0]

        ### Train discriminator: max log(D(real)) + log(1 - D(Z))
        noise = torch.randn(batch_size, z_dim).to(device)
        fake = gen(noise)
        
        disc_real = disc(real).view(-1)
        lossD_real = criterion(disc_real, torch.ones_like(disc_real))

        disc_fake = disc(fake).view(-1)
        lossD_fake = criterion(disc_fake.detach(), torch.zeros_like(disc_fake))

        lossD = (lossD_real + lossD_fake)/2

        disc.zero_grad()
        lossD.backward()
        opt_disc.step()

        # Train Generator MIN log(1- D(G(Z))) <-----> max log(D(G(Z)))
        output = disc(fake).view(-1)
        lossG = criterion(output, torch.ones_like(output))
        gen.zero_grad()

        opt_gen.step()

        if batch_idx==0:
            print(
               f'Epoch [{epoch}/{epochs}] Loss D: {lossD:.4f}, Loss G {lossG:.4f}'
            )

            with torch.no_grad():
                fake = gen(fixed_noise).reshape(-1, 1, 28, 28)
                data = real.reshape(-1, 1, 28, 28)
                img_grid_fake = torchvision.utils.make_grid(fake, normalize=True)
                img_grid_real = torchvision.utils.make_grid(data, normalize=True)

                writer_fake.add_image(
                    "Mnist Fake Images", img_grid_fake, global_step=step
                )
                writer_real.add_image(
                    "Mnist Real Images", img_grid_real, global_step=step
                )
                step += 1