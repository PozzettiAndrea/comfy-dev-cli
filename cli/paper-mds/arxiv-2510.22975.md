# VOMP: PREDICTING VOLUMETRIC MECHANICAL PROPERTY FIELDS

Rishit Dagli1,<sup>2</sup> Donglai Xiang<sup>1</sup> Vismay Modi<sup>1</sup> Charles Loop<sup>1</sup> Clement Fuji Tsang<sup>1</sup> Anka He Chen<sup>1</sup> Anita Hu<sup>1</sup> Gavriel State<sup>1</sup> David I.W. Levin1,<sup>2</sup> Maria Shugrina<sup>1</sup> <sup>1</sup>NVIDIA <sup>2</sup>University of Toronto

<https://research.nvidia.com/labs/sil/projects/vomp>

![](_page_0_Figure_5.jpeg)

<span id="page-0-0"></span>Figure 1: VoMP predicts physically accurate volumetric mechanical property fields across 3D representations in just a few seconds (top), enabling their use in realistic deformable simulations (bottom).

### ABSTRACT

Physical simulation relies on spatially-varying mechanical properties, often laboriously hand-crafted. VoMP is a feed-forward method trained to predict Young's modulus (E), Poisson's ratio (ν), and density (ρ) throughout *the volume* of 3D objects, in any representation that can be rendered and voxelized. VoMP aggregates per-voxel multi-view features and passes them to our trained Geometry Transformer to predict per-voxel material latent codes. These latents reside on a space of physically plausible materials, which we learn from a real-world dataset, guaranteeing the validity of decoded per-voxel materials. To obtain object-level training data, we propose an annotation pipeline combining knowledge from segmented 3D datasets, material databases, and a vision-language model, along with a new benchmark. Experiments show that VoMP estimates accurate volumetric properties, far outperforming prior art in accuracy and speed.

### 1 INTRODUCTION

Accurate physics simulation is a critical part of modern design and engineering, for example, in workflows like creating Digital Twins (virtual replicas of real systems) [\(Grieves & Vickers, 2017\)](#page-12-0), Real-2-Sim (generating digital simulation from the real world) [\(NVIDIA, 2019\)](#page-15-0), and Sim-2-Real (transferring policies trained in simulation to real-world deployment) [\(Rudin et al., 2021\)](#page-16-0). However, setting up reliable simulations remains labor-intensive, partially due to the necessity to provide accurate mechanical properties *throughout the volume* of every object, namely the spatially-varying Young's Modulus (E), Poisson's ratio (ν), and density (ρ). Common 3D capture methods [\(Kerbl](#page-13-0) [et al., 2023\)](#page-13-0) and 3D repositories [\(Deitke et al., 2023\)](#page-11-0) rarely contain such annotations, forcing artists and engineers to guess or copy-paste coarse material presets in a subjective, time-consuming process. We focus on automatic prediction of these parameters, addressing important limitations of prior art.

We propose VoMP, *the first feed-forward model trained to estimate simulation-ready mechanical property fields* (E, ν, ρ) *within the volume of 3D objects across representations*. Rather than specializing on inputs like Gaussian Splats [\(Shuai et al., 2025;](#page-16-1) [Xie et al., 2024\)](#page-17-0), our method works for any geometry that can be voxelized and rendered from turnaround views, including meshes, Gaussian Splats, NeRFs and SDFs (Fig. [1\)](#page-0-0). Unlike virtually all prior works, VoMP is fully feedforward, requiring no per-object optimization of feature fields [\(Zhai et al., 2024;](#page-18-0) [Shuai et al., 2025\)](#page-16-1) or run-time aggregation of Vision-Language Model (VLM) [\(Lin et al., 2025a\)](#page-13-1) or Video Model [\(Lin](#page-14-0) [et al., 2025b\)](#page-14-0) supervision. Uniquely among others, VoMP outputs true mechanical properties (a.k.a. material parameters), like those measured in the real world. Many existing pipelines target fast, approximate simulators, resulting in simulator-specific parameters [\(Zhang et al., 2025;](#page-18-1) [Huang et al.,](#page-13-2) [2024b\)](#page-13-2) that may not transfer reliably across frameworks (Fig. [2\)](#page-1-0), whereas our result is directly compatible with any accurate simulator. Finally, unlike prior art, our method is designed to assign materials throughout the object volume, which is critical for simulation fidelity.

To enable learning physically valid mechanical properties, we first train a latent space on a database of real-world values (E, ν, ρ) using a variational auto-encoder MatVAE ([§3\)](#page-3-0). To predict mechanical property fields for 3D objects, our method first voxelizes the input geometry and aggregates multiview image features across the voxels ([§4.1\)](#page-4-0). This process accepts many representations[1](#page-1-1) and is fast, unlike optimization used in concurrent work [\(Le et al., 2025\)](#page-13-3). We pass the voxel features through the Geometry Transformer ([§4.2\)](#page-4-1), trained to output per-voxel material latents. The MatVAE latent space decouples learning material assignments for objects from learning what materials are valid, ensuring that the final volumetric properties (E, ν, ρ) decoded by MatVAE are physically valid, even in the case of interpolation. To create material property fields for training, we propose a pipeline ([§5\)](#page-5-0) combining the knowledge from part-segmented 3D assets, material databases, visual textures, and a VLM. Our experiments ([§6\)](#page-5-1) show that VoMP estimates simulation-ready spatially-varying mechanical properties across a range of object classes and representations, resulting in realistic elastodynamic simulations. We evaluate our method on an existing mass prediction benchmark and contribute a new material estimation benchmark ([§6.3\)](#page-6-0), consistently outperforming prior art [\(Shuai](#page-16-1) [et al., 2025;](#page-16-1) [Lin et al., 2025a;](#page-13-1) [Zhai et al., 2024\)](#page-18-0). In summary, our contributions are:

- The first (to our knowledge) method to estimate object mechanical material property fields that *(1)* is a trained feed-forward model with minimal preprocessing, *(2)* generalizes across 3D representations, *(3)* predicts physically valid properties that can be used with an accurate simulator, and *(4)* predicts mechanical properties *within the volume* of objects ([§4\)](#page-4-2).
- The first (to our knowledge) mechanical properties latent space ([§3\)](#page-3-0).
- An automatic data annotation pipeline and a new benchmark for volumetric physics materials ([§5\)](#page-5-0).
- Thorough evaluation through high-fidelity simulations and quantitative metrics on existing and new benchmarks, significantly outperforming the prior art ([§6\)](#page-5-1).

### 2 RELATED WORK

### <span id="page-1-2"></span>2.1 BACKGROUND

All algorithms for continuum-based simulation of solids and liquids require material models as input. The material, or constitutive, model is the function that determines the force response of a class of materials (e.g., rubbers, snow, water) to internal strains and strain rates. To produce the correct constitutive behavior for a given material, the model requires an accurate set of corresponding material parameters for every point in the simulated volume. For locally isotropic material models, Young's modulus (E, in the 1D linear regime, the proportionality constant between stress and strain), Poisson's ratio (ν, the negative ratio of transverse to axial strain under uniaxial loading) and density (ρ, unit mass per volume) are ubiquitous. Given an accurate and valid triplet (E, ν, ρ) along with a reasonable material model, a consistent numerical simulation can

<span id="page-1-0"></span>![](_page_1_Figure_10.jpeg)

Figure 2: Simulator differences when dropping a solid sphere with (E, ν, ρ) = (10<sup>4</sup>P a, 0.3, 10<sup>3</sup> kg/m<sup>3</sup> ) with XPBD [\(Macklin et al., 2016\)](#page-14-1) and MPM [\(Sulsky et al., 1994\)](#page-16-2) vs. more accurate FEM.

produce accurate predictions of an object's behavior under load. Measured, real-world parameters

<span id="page-1-1"></span><sup>1</sup>We describe available methods for meshes, SDFs, and NeRFs, and present a method for Splats in [§6.1.](#page-5-2)

are portable to any consistent simulation algorithm (we use high-resolution Finite Element Methods). Further, they are portable across any material model that relies on density, Young's modulus and Poisson's ratio, or derived quantities, such as shear or bulk modulus (e.g., Neo-Hookean, St. Venant–Kirchhoff, As-Rigid-As-Possible, Co-Rotated Elastic, Mooney–Rivlin, and Ogden models). On the other hand, many physics simulation algorithms are not implemented or applied in a consistent fashion, favoring speed over accuracy [\(Macklin et al., 2016;](#page-14-1) [Sulsky et al., 1994\)](#page-16-2). In these cases, material parameters must be modified to avoid inaccurate behavior (Fig. [2\)](#page-1-0).

### <span id="page-2-0"></span>2.2 INFERRING MECHANICAL PROPERTIES OF STATIC OBJECTS

Our goal is to predict volumetric mechanical properties given only shape and appearance, a challenging inverse problem, which research suggests humans learn good intuition about [\(Adelson, 2001;](#page-10-0) [Fleming, 2014;](#page-12-1) [Fleming et al., 2013;](#page-12-2) [Sharan et al., 2009\)](#page-16-3). However, progress in learning-based approaches has been hampered by limited data. Existing datasets are small [\(Gao et al., 2022;](#page-12-3) [Downs](#page-11-1) [et al., 2022;](#page-11-1) [Chen et al., 2025c\)](#page-11-2), contain noisy labels [\(Lin et al., 2018\)](#page-13-4), use simulator-specific parameters [\(Mishra, 2024;](#page-14-2) [Xie et al., 2025;](#page-17-1) [Belikov et al., 2015\)](#page-10-1), provide only coarse annotations [\(Ahmed](#page-10-2) [et al., 2025;](#page-10-2) [Slim et al., 2023;](#page-16-4) [Li et al., 2022\)](#page-13-5) or are biased towards rigid or man-made objects [\(Cao](#page-11-3) [et al., 2025\)](#page-11-3). Worse, data collection is difficult, relying on rigorous physical experiments [\(ASTM](#page-10-3) [Committee D20, 2022;](#page-10-3) [ASTM Committee E28, 2024;](#page-10-4) [Pai, 2000\)](#page-15-1), and even then lacking spatial material fields [\(Loveday et al., 2004\)](#page-14-3) due to digitization and annotation challenges.

As a result, works that infer physical properties from appearance often leverage knowledge from large pre-trained models. NeRF2Physics [\(Zhai et al., 2024\)](#page-18-0) and PUGS [\(Shuai et al., 2025\)](#page-16-1) optimize language-embedded feature fields for a NeRF [\(Mildenhall et al., 2020\)](#page-14-4) or 3D Gaussians [\(Kerbl](#page-13-0) [et al., 2023\)](#page-13-0), respectively, to predict coarse stiffness categories and density, but require per-object optimization and are limited in their ability to predict values inside objects due to the lack of meaningful features inside NeRFs or splats. Many approaches distill signals from a Video Generation Model and optimize physics parameters by backpropagating through fast, approximate physics simulators, resulting in a slow optimization process, yielding materials deviating from real-world values and overfit to a specific simulation setup [\(Zhang et al., 2025;](#page-18-1) [Huang et al., 2024b;](#page-13-2) [Liu et al., 2025;](#page-14-5) [Cleac'h et al., 2023;](#page-11-4) [Liu et al., 2024a;](#page-14-6) [Lin et al., 2025b\)](#page-14-0) ([§2.1\)](#page-1-2). Many methods are also tailored to a specific 3D representation or real-time simulation implementations, such as Splats [\(Xie et al., 2024\)](#page-17-0) or explicit Material Point Methods [\(Sulsky et al., 1994;](#page-16-2) [Le et al., 2025\)](#page-13-3), or work with coarse material categories [\(Fischer et al., 2024;](#page-12-4) [Hsu et al., 2024;](#page-12-5) [Lin et al., 2025a;](#page-13-1) [Xia et al., 2025\)](#page-17-2) that must be manually mapped to simulation parameters. Instead, we aim to augment objects across 3D representations with fine-grained spatially-varying mechanical properties that are physically accurate and compatible across accurate simulators. Like our method, many techniques leverage vision-language (VLM) models. PhysGen [\(Liu et al., 2024b\)](#page-14-7) and PhysGen3D [\(Chen et al., 2025a\)](#page-11-5) use a VLM to infer mass, elasticity, and friction for segmented parts of a single image. Phys4DGen [\(Lin et al., 2025a\)](#page-13-1) uses a VLM to annotate parts of a 3D model with coarse material labels, which are then mapped to physical parameters, a baseline used in our evaluation. Most works above rely on aggregation of large model outputs for every input shape, which can be brittle and time-consuming at run-time, and can only leverage external segmentation. Instead, our method uses a VLM paired with other data sources to annotate a *training dataset* for a feed-forward model leveraging 3D data to annotate and learn internal material composition.

Like our method, SOPHY [\(Cao & Kalogerakis, 2025\)](#page-10-5), PhysX-3D [\(Cao et al., 2025\)](#page-11-3), PhysSplat [\(Zhao et al., 2024a;](#page-18-2)[b\)](#page-18-3) (a.k.a. SimAnything) and the concurrent Pixie [\(Le et al., 2025\)](#page-13-3) leverage pretrained models and 3D data to annotate a *training* dataset with physical materials. PhysSplat trains a network to predict spatially-varying simulator-specific material offset weights for MPM by using outputs from video distillation [\(Liu et al., 2024a\)](#page-14-6), not focusing on material accuracy. SOPHY and PhysX-3D are 3D generative models, designed to generate new shapes augmented with physical attributes, and cannot augment existing assets, which is our goal. Still, we detail similar aspects of these works. Like these works, our method uses a VLM to annotate 3D objects with Young's Modulus, Poisson's ratio, and density, but we do not rely on the human-in-the-loop and instead leverage multiple data sources, not just VLM knowledge, to ensure more accurate physical properties. As a baseline, SOPHY does implement a material decoder, but it has not been made available, and only considers object surface, while we aim to estimate volumetric properties. Like our method, PhysX-3D adopts the structural latent space of TRELLIS, but trains a joint generative model over these and learned shape-aware physical properties latents in order to generate physics-augmented shapes from

<span id="page-3-1"></span>![](_page_3_Figure_1.jpeg)

Figure 3: **VoMP Overview.** For any input geometry, we aggregate multi-view DINOv2 features across its volumetric voxelization (§4.1). A trained GeometryTransformer (§4.2) predicts per-voxel material latents, decoded by MatVAE (§3) into mechanical properties  $(E, \nu, \rho)$ .

scratch. In contrast, we treat material prediction as deterministic inference for simplicity, and further adjust the TRELLIS pipeline to facilitate accurate material prediction inside the object. Pixie (Le et al., 2025), a concurrent work and the only other feed-forward approach, is trained on semantically-segmented objects and uses points from filtering NeRF densities. Thus, Pixie is trained on segments biased toward the surface, as we show in Fig. 15, while we demonstrate being able to estimate volumetric properties with internal structures. Furthermore, unlike Pixie, we specifically focus on estimating physically plausible material properties, such as those measured in the real world.

### <span id="page-3-0"></span>3 MECHANICAL PROPERTIES LATENT SPACE

To learn a latent space of valid Young's modulus, Poisson's ratio, and density triplets  $(E, \nu, \rho)$  (§2.1), we propose MatVAE, a variational autoencoder (VAE) trained on a dataset of real-world values  $\{m_i := (E_i, \nu_i, \rho_i)\}$  (§5.1). The model's objective is to map these triplets m into a 2-dimensional latent space,  $z \in \mathbb{R}^2$ , from which they can be accurately reconstructed. While this offers only minor compression ( $\mathbb{R}^3 \to \mathbb{R}^2$ ), this latent 2D space of material properties is now easy to visualize, sample, and interpolate within, and results in consistent distances between material triplets with disparate units (Fig. 7,§6.4). MatVAE acts like a continuous tokenizer that allows us to always ensure VoMP output properties that fall inside the range of some materials.

We build on VAE (Kingma & Welling, 2022), with the reconstruction component of the loss defined as mean-squared error between the input  $(E_i, \nu_i, \rho_i)$  and reconstructed material values  $(\hat{E}_i, \hat{\nu}_i, \hat{\rho}_i)$ :

$$\mathcal{L}_{\text{Recon}} = \frac{1}{N} \sum_{i=1}^{N} \left\| ((E_i, \nu_i, \rho_i)^N)^\mathsf{T} - ((\hat{E}_i, \hat{\nu}_i, \hat{\rho}_i)^N)^\mathsf{T} \right\|_2^2, \tag{1}$$

where T denotes transpose and N per-property normalization, where E and  $\rho$  are first log-transformed ( $\log_{10}(E)$ ,  $\log_{10}(\rho)$ ), then normalized to [0,1], while  $\nu$  is directly normalized to [0,1]. We find other normalization schemes without log-transform or standard z-score normalization induce a heavy-tailed feature distribution, which is poorly conditioned for learning (§C).

We make several modifications over standard VAE. *First*, to capture a complex posterior beyond a simple Gaussian, the encoder's output is transformed by a (radial) Normalizing Flow (Rezende & Mohamed, 2015), giving us a more flexible variational distribution  $q_{\phi}(z|m)$  since we observe heavy-tailed distribution for Young's Modulus and Density while Poisson's Ratio concentrates near the boundaries after normalization. *Second*, we decompose the KL-divergence term of the ELBO following (Chen et al., 2018). This allows us to directly penalize the total correlation  $TC(z) = KL(\bar{q}_{\phi}(z)||\prod_j \bar{q}_{\phi}(z_j))$  where  $\bar{q}_{\phi}(z)$  is the aggregated posterior,  $z_j$  is the  $j \in \{1,2\}$ -th coordinate of the latent vector z. Penalizing TC allowed us to reduce the high dependence between latent coordinates which caused MatVAE to encode density in both dimensions. *Third*, we observe imbalanced reconstruction, *i.e.* the latent space collapses to one property, giving us low reconstruction errors for one property and high reconstruction error for others (§C). Thus, to ensure the 2 latent dimensions are actively utilized, we introduce a capacity constraint ( $\delta \times z_{\text{dim}}$ ) based

on (Higgins et al., 2017), resulting in the following final objective:

$$\mathcal{L}_{\text{MatVAE}} = \underbrace{\mathcal{L}_{\text{Recon}}}_{\text{MSE}} + \underbrace{\frac{\gamma \cdot \text{MI}(z)}{\gamma \cdot \text{MI}(z)} + \underbrace{\beta \cdot \text{TC}(z)}_{\text{Total Correlation}} + \alpha \cdot \sum_{j=1}^{d} \underbrace{\max(\delta, \text{KL}(q_{\phi}(z_{j}) \parallel p(z_{j})))}_{\text{Dimension-wise KL}},$$
(2)

where we set  $\gamma$ ,  $\beta$ ,  $\alpha = (1.0, 2.0, 1.0)$ , with a free nats constraint  $\delta = 0.1$ . See §F.1 for more details.

### <span id="page-4-2"></span>4 PREDICTING MECHANICAL PROPERTY FIELDS

To predict volumetric mechanical properties across 3D representation, VoMP first aggregates volumetric features for the input geometry (§4.1), which are then processed by a trained feed-forward transformer model (§4.2) that learns in the latent space of MatVAE (§3). See §2.2.

### <span id="page-4-0"></span>4.1 AGGREGATING FEATURES

Our method accepts any 3D representation that can be voxelized and rendered from multiple views. Following recent works (Wang et al., 2023; Dutt et al., 2024; Xiang et al., 2025), we compute rich DINOv2 (Oquab et al., 2024) image features across 3D views and lift them to 3D by projecting each voxel center into every view using the camera parameters to retrieve the corresponding image features. The retreived image features are then averaged to obtain a feature for every voxel. A critical difference with these prior works is that we also voxelize and process the interior of the objects and not just their surface, which allows us to learn and predict material properties *inside* the objects (See §6.1 for voxelization schemes and see §F.3 for details on voxelization for training). Let's denote all active voxel center positions in a 3D grid of size  $N^3$  as  $\{\mathbf{p}_i\}_{i=1}^L$  where L denotes the number of voxels,  $\mathbf{p}_i \in \mathbb{R}^3$  denotes the voxel center, and  $\Pi_j: \mathbb{R}^3 \to [-1,1]^2$  the camera projection for view  $j \in J$  where J is the set of rendered views. Let the DINOv2 patch-token map be  $T_j \in \mathbb{R}^{1024 \times n \times n}$  which is bilinearly sampled to get a feature map  $\mathcal{F}_j: [-1,1]^2 \to \mathbb{R}^{1024}$ . Then for each voxel  $i \in \{1,2,\ldots,L\}$ , we obtain a feature  $\mathbf{f}_i$ :

$$\mathbf{f}_{i} = \text{Average}(\mathcal{C}_{i} = \left\{ \mathcal{F}_{j}(\Pi_{j}(\mathbf{p}_{i})) \mid j \in J \right\}) \in \mathbb{R}^{1024}$$
(3)

This propagates multi-view information to the voxels in the interior of the object, encoding useful information that our model learns to process to predict internal material composition.

#### <span id="page-4-1"></span>4.2 Geometry Transformer

The main component of VoMP is a Transformer F that maps voxelized image features to our trained material latent representation. The backbone of our model follows TRELLIS (Xiang et al., 2025) encoder/decoder, and the backbone layers of our model are initialized with TRELLIS weights. The encoder processes a variable-length set of active voxels, represented by their positions and features  $\mathbf{X} = \{(\mathbf{p}_i, \mathbf{f}_i)\}_{i=1}^L$ . To make this data suitable for a Transformer, we first serialize the voxel features into a sequence and then inject spatial awareness by adding sinusoidal positional encodings derived from each voxel's 3D coordinates. Similar to TRELLIS and state-of-the-art 3D Transformers, we adopt a 3D shifted window attention mechanism (Liu et al., 2021; Yang et al., 2025). Contrary to TRELLIS (Xiang et al., 2025), to handle assets of various sizes, we define a maximum sequence length of  $L_N$ . For assets with fewer voxels  $L \leq L_N$ , we use the complete set. However, for larger assets where  $L > L_N$ , we use a stochastic sampling strategy, selecting a random subset of  $L_N$  voxels at the start of each training epoch. This dynamic resampling ensures the model is exposed to different parts of the asset over epochs and have a larger number of "effective" max voxels.

For each training asset, we first define  $\mathcal{S}$  as the set of voxel indices to be processed in the current iteration. The corresponding sequence of image features  $\mathbf{X}_{\mathcal{S}}$  obtained from voxel features (§4.1), is passed to  $\mathbf{F}$ . The resulting latent representation is then fed into the frozen decoder of pre-trained MatVAE to predict material properties. The MatVAE is run L times i.e. once per voxel, which gives us material triplets  $(E, \nu, \rho)$  for each voxel. We train this transformer with the mean squared error between the predicted materials and the ground truth materials, averaged over all voxels in the set  $\mathcal{S}$ ,

<span id="page-4-3"></span>
$$\mathcal{L}_{\mathbf{F}} = \frac{1}{|\mathcal{S}|} \sum_{i \in \mathcal{S}} \|\mu_{\theta}(\mathbf{F}(\mathbf{X}_{\mathcal{S}})_i) - ((E_i, \nu_i, \rho_i)^N)^{\mathsf{T}}\|_2^2, \tag{4}$$

where µθ(·) denotes the output of the frozen MatVAE decoder, ((E<sup>i</sup> , ν<sup>i</sup> , ρi) <sup>N</sup> ) <sup>T</sup> is the ground truth material vector for voxel i, and F(X<sup>S</sup> )<sup>i</sup> is the latent representation for voxel i.

To transfer voxel materials back to the original representation (*i.e.* splat means, tets for FEM simulation, quadrature points for simulation, etc.), we use nearest neighbour interpolation as outlined in [§G.1.](#page-44-0) The per-voxel latents are passed into the decoder model of MatVAE ([§3\)](#page-3-0), which yields per-voxel material triplets, as shown in [§2.2.](#page-3-1)

### <span id="page-5-0"></span>5 TRAINING DATA GENERATION

### <span id="page-5-3"></span>5.1 MATERIAL TRIPLETS DATASET (MTD)

To train MatVAE ([§3\)](#page-3-0), we collect Material Triplet Dataset(MTD), containing 100,562 triplets (E, ν, ρ) for real-world materials. We first collect a dataset of measured material properties from multiple online databases [\(MatWeb, LLC, 2025;](#page-14-9) [Wikipedia contributors, 2024a](#page-16-7)[;b;](#page-16-8)[c;](#page-16-9) [The Engineer](#page-16-10)[ing Toolbox, 2024;](#page-16-10) [Department of Engineering, University of Cambridge, 2011\)](#page-11-7), containing values obtained experimentally, typically with valid *ranges* for all three properties for all materials. We sample numeric triplets from each material, with the number of samples proportional to the range size. Finally, we filter out duplicates resulting from overlapping ranges for some materials.

### 5.2 GEOMETRY WITH VOLUMETRIC MATERIALS (GVM) DATASET

To train Geometry Transformer ([§4\)](#page-4-2), we develop an automatic annotation pipeline to overcome the limited availability of detailed volumetric material datasets ([§2.2\)](#page-2-0). Like prior works [\(Lin et al., 2025a;](#page-13-1) [Cao & Kalogerakis, 2025;](#page-10-5) [Le et al., 2025\)](#page-13-3), we leverage a pre-trained VLM, but overcome its limitations by introducing *additional sources of knowledge* present in our 3D dataset and the MTD([§5.1\)](#page-5-3). We collect high-quality 3D meshes from [\(NVIDIA](#page-15-3) [Corporation, 2025a](#page-15-3)[;c;](#page-15-4) [NVIDIA Developer, 2025;](#page-15-5) [NVIDIA Corporation, 2025d\)](#page-15-6), containing 1624 part-

<span id="page-5-4"></span>![](_page_5_Figure_8.jpeg)

Figure 4: Training Data annotation leverages accurate 3D data labels together with a VLM.

segmentated 3D models, with a total of 8089 parts, and treat each part as having isotropic material. Each part contains an English material name and its own realistic PBR texture, which can be used as additional cues to the VLM. For each part in each object, we pass the following information to the VLM: rendering of the full object, detail rendering of the part's visual material mapped onto a sphere (showing visual aspects that tend to correlate with material composition), the material names, and the ranges of three closest real-world materials in the MTD ([§5.1\)](#page-5-3) based on the material names (See Fig[.4,](#page-5-4) detailed prompt in Fig. [23\)](#page-50-0). The vision-language model then outputs material triplets for each part, and we map to all volumetric voxels within it, resulting in a total of 37M voxels annotated with (E, ν, ρ). By guiding VLM with real-world material values and extra clues, we avoid inaccuracies and implausible material values. See additional details in [§6.1,](#page-5-2) [§E.](#page-33-0)

## <span id="page-5-1"></span>6 EXPERIMENTS AND RESULTS

We evaluate VoMP end-to-end, showing diverse realistic simulations in [§6.2.](#page-6-1) Quantitative results are presented in [§6.3,](#page-6-0) with MatVAE evaluated separately in [§6.4.](#page-7-0) See video and [§A](#page-21-0) for many additional results, [§B](#page-28-1) for extra comparisons with concurrent work and [§C](#page-29-0) for ablations.

### <span id="page-5-2"></span>6.1 IMPLEMENTATION DETAILS

Voxelization: For voxelizing 3D Gaussian splats [\(Kerbl et al., 2023\)](#page-13-0), we present *a new voxelizer*, that works in three phases: (1) 3D Gaussians are voxelized over a 3D grid as solid ellipsoids defined by the 99th percentile iso-surface, (2) this set of voxels is rendered from several dozen viewpoints sampled over a sphere to form depth maps, (3) these depthmaps are used to carve away empty space around the exterior of the object, but leaving unseen *interior* voxels to form a solid approximation of the object. We then sample this solid at jittered sample points on a regular grid. We employ

<span id="page-6-3"></span>Figure 5: **Simulation-ready physics materials of VoMP** enable realistic simulations for meshes and splats. octrees as acceleration structures and GPU implementations for both phases. Our test objects can be voxelized in 31 ms (see Tb. 1). To voxelize meshes and SDFs we use standard methods (see §F.3).

**Data and Training:** For material annotation, we experimentally choose Qwen 2.5 VL-72B VLM (Bai et al., 2023; 2025). We partition our MTD and GVM datasets ( $\S 5$ ) into 80-10-10 train, validation, and test sets. See  $\S E$  for data details. For rendering we use Omniverse (NVIDIA Corporation, 2025b) and Blender (Blender Online Community, 2021), and for DINOv2 we use an optimized implementation (NVIDIA, 2025). During training and testing, we set the maximum number of nonempty voxels per object  $L_N=32768$  (sampled stochastically,  $\S 4.2$ ), and sparse data structures for efficiency. See  $\S F$  for more details. All experiments were performed on a machine with four 80GB A100 GPUs, where training took about 12 hours for MatVAE and 5 days for the Transformer.

**Simulation:** We used FEM simulator for meshes and sparse Simplicits (Modi et al., 2024; Fuji Tsang et al.) for our large-scale simulations combining splats and meshes. Details in §G.

### <span id="page-6-1"></span>6.2 END-TO-END QUALITATIVE EVALUATION

We qualitatively evaluate VoMP by using it to annotate volumetric mechanical fields for several meshes and 3D Gaussian Splats, and running physics simulation with these exact spatially varying  $(E, \nu, \rho)$  values, resulting in realistic simulations without any hand-tweaks (Fig. 5, Fig. 8,  $\blacksquare$ : 0:36). We also show that our approach can work across more representations, including meshes, 3D Gaussian Splats, SDF, and NeRFs (Fig. 8a, with additional results in §A.2.

### <span id="page-6-0"></span>6.3 QUANTITATIVE EVALUATION

**Datasets and Metrics:** The 10% hold-out test set of GVM (§5) consists of 166 high-quality 3D objects with per-voxel mechanical properties for a total of 4.9 million point annotations, significantly larger than previous works, e.g. 31 points across 11 objects (Zhai et al., 2024). We contribute this as a new benchmark and use it for evaluation against baselines. We measure standard metrics, Average Log Displacement Error (ALDE), Average Displacement Error (ADE), Average Log Relative Error (ALRE), and Average Relative Error (ARE) for each mechanical property, further detailed in §D.1. We provide additional intuition for interpreting these errors through targeted simulations in §D.4.

<span id="page-6-2"></span>Table 1: Wall-clock comparisons and breakdown.

| Method                 | Time (s)                  |
|------------------------|---------------------------|
| NeRF2Physics           | 1454.55 (±1118)           |
| PUGS                   | 1058.33 (±6.94)           |
| Pixie                  | 201.63 (±27.74)           |
| Phys4DGen*             | <u>51.65</u> (±4.07)      |
| Ours                   | <b>3.59</b> (±1.36)       |
| Rendering              | 2.11 (±0.0540)            |
| Voxelization           | $0.03 \ (\pm 0.0016)$     |
| DINO-v2 Computation    | $0.86 \pm 0.0020$         |
| DINO-v2 Reconstruction | $0.58 \ (\pm 0.0053)$     |
| Geometry Transformer   | $0.0082 \ (\pm 0.0063)$   |
| MatVAE                 | $0.00032 \ (\pm 0.00026)$ |

Baselines: We compare against prior art NeRF2Physics (Zhai et al., 2024) and PUGS (Shuai et al., 2025), where we look up material properties at the voxel locations (with proper scaling) using their optimized representations. Note that these techniques do not output Poisson's ratio. Phys4DGen (Lin et al., 2025a) is an important baseline, aggregating VLM prediction directly, but does not provide code. We used our best effort to replicate their method and used prompts provided by the authors, designating this implementation Phys4DGen\*. More baseline details in §F.5. We also include early comparisons against concurrent

(and as yet unpublished) Pixie (Le et al., 2025), with additional explorations in §B.

**Estimating Mechanical Properties:** Quantitative evaluation of material estimates  $(E, \nu, \rho)$  of our method against prior art on our new detailed benchmark shows a *dramatic quality boost across all properties and metrics* (Fig. 6b). According to our explorations (§D.4), ALRE under 0.05 for E and ARE under 0.15 for other properties result in similar simulations, suggesting that our materials will

<span id="page-7-1"></span>Table 2: **Mechanical Property Estimates** of our method on the *publicly released dataset* are very close to the full dataset. Per-voxel error rate is first computed per object, then averaged across all objects in the test set to avoid weighing some objects more. Global voxel-level normalization yields similar results, see Supplement Tb. 3.

| Method               | Young's Modulus Pa $(E)$         |                                  | Poisson's                       | Ratio $(\nu)$                   | Density $\frac{kg}{m^3}$ ( $\rho$ )         |                                  |  |
|----------------------|----------------------------------|----------------------------------|---------------------------------|---------------------------------|---------------------------------------------|----------------------------------|--|
|                      | ALDE (↓)                         | ALRE (↓)                         | ADE (↓)                         | ARE (↓)                         | ADE (↓)                                     | ARE (↓)                          |  |
| NeRF2Physics<br>PUGS | 2.8000 (±1.05)<br>3.3942 (±1.72) | 0.1346 (±0.05)<br>0.1688 (±0.10) | -                               | -                               | 1432.0343 (±964.88)<br>3568.2150 (±2839.13) | 1.0365 (±0.63)<br>3.2429 (±3.56) |  |
| Phys4DGen*           | 4.8967 (±3.17)                   | 0.2227 (±0.14)                   | $\underline{0.0407}~(\pm 0.04)$ | $\underline{0.1467}~(\pm 0.18)$ | 1865.5673 (±2176.90)                        | 1.4394 (±2.35)                   |  |
| Ours                 | 0.3794 (±0.29)                   | 0.0409 (±0.04)                   | 0.0241 (±0.01)                  | 0.0818 (±0.03)                  | 142.7017 (±166.92)                          | 0.0921 (±0.07)                   |  |

lead to more faithful simulations than competitors when using an accurate simulator. Qualitatively (Fig. 6a), we observe that this performance difference may be due to baselines occasionally mislabeling segments (e.g. by Phys4DGen), due to noisy estimates (e.g. NeRF2Physics and PUGS), and less accurate values in the objects' interior due to the baselines' design.

We are unable to make the vegetation subset of our dataset publicly available. Thus, we compute the mechanical property estimations on the public version of the dataset in Tb. 2 and 3. We find that our results averaged over the public dataset are highly similar to the full dataset.

**Run-Time:** To show approximate speed difference, we report average material estimate speeds across 100 runs on objects with an average of 53.9K Gaussians for our method and the baselines in Tb. 1. To ensure fair compute between CPU and GPU heavy methods, we ran this experiment on a machine with only one A100 GPU and 64 CPUs. While we do not provide timing breakdown of the other methods, this result suggests a speed up of 5-100x achieved by our method, which is not surprising given that it is the only feed-forward model among previous work. Concurrent Pixie, which is also feed-forward, involves a heavier pre-processing step, including per-object optimization, affecting its end-to-end time. In the timing breakdown of our method, rendering and pre-processing take the most time, and could be further optimized.

**Mass Estimation:** Following NeRF2Physics (Zhai et al., 2024) and PUGS (Shuai et al., 2025), we also evaluate our dataset on the ABO-500 (Collins et al., 2022) object mass estimation benchmark, following the evaluation protocol of PUGS. We run our model to estimate density  $\rho$  for upto 32678 voxels per object, then average these values and multiply by the known object volume to obtain mass. While this is only an imperfect proxy for measuring the accuracy of volumetric density  $\rho$ , it is a benchmark used by prior works, and we include it for completeness. We achieve better or on-par performance across most metrics (Fig. 6c), with qualitative results in §A.3.

**Validity:** To gauge how well different methods are at predicting realistic materials, such as those measured in the real world, which is our goal, we leverage our MTD dataset of real materials. First, we run all methods on GVM test set objects, and for each test voxel compute relative errors to the nearest possible material range from MTD (error is 0 for estimates within an existing material range). These errors are averaged across all the voxels and reported in Fig. 6d. We observe that our method, on average, outputs much more realistic materials, as it was explicitly designed to do so.

### <span id="page-7-0"></span>6.4 RECONSTRUCTING AND GENERATING MATERIALS WITH MATVAE

Given no prior works exploring a latent space of material triplets  $(E, \nu, \rho)$ , we evaluate MatVAE on the MTD test set (§6.1), achieving low reconstruction errors in Fig. 7a (See §D.1, §D.4) for metrics). Further, in Fig. 7 we show the desirable properties of this learned latent space. In (a), samples throughout the 2D latent space map to real-world material ranges in MTD. In (b), we show that  $(E, \nu, \rho)$  values of real materials encoded to the latent space vary smoothly. Further, the latent space ensures valid interpolation points between materials (c), facilitating valid assignment from predicted voxel materials back to the original geometry. We include detailed ablations of MatVAE design (§C), and additional latent space explorations (§A.4).

#### 7 DISCUSSION

We introduce a representation-agnostic method that maps any 3D asset (mesh, SDF, Gaussian splat, or voxel grid) to a volumetric field of physically valid mechanical properties  $(E, \nu, \rho)$ . We show

<span id="page-8-0"></span>![](_page_8_Figure_1.jpeg)

(a) **Qualitative Comparison:** We show that qualitative VoMP tends to provide less noisy volumetric? values compared to the baselines. We show the color coded fields and slice planes through the fields.

| Method                             | Young's Modulus Pa $(E)$                           |                                                                                                              | Poisson's           | Ratio $(\nu)$            | Density $\frac{kg}{m^3}(\rho)$                                      |                                                    |  |
|------------------------------------|----------------------------------------------------|--------------------------------------------------------------------------------------------------------------|---------------------|--------------------------|---------------------------------------------------------------------|----------------------------------------------------|--|
|                                    | ALDE (↓)                                           | ALRE (↓)                                                                                                     | ADE (↓)             | ARE (↓)                  | $ADE(\downarrow)$                                                   | ARE (↓)                                            |  |
| NeRF2Physics<br>PUGS<br>Phys4DGen* | 2.8000 (±1.05)<br>3.3942 (±1.72)<br>4.8967 (±3.17) | $\begin{array}{c} \underline{0.1346} \ (\pm 0.05) \\ 0.1688 \ (\pm 0.10) \\ 0.2227 \ (\pm 0.14) \end{array}$ | -<br>0.0407 (±0.04) | -<br>-<br>0.1467 (±0.18) | 1432.0343 (±964.88)<br>3568.2150 (±2839.13)<br>1865.5673 (±2176.90) | 1.0365 (±0.63)<br>3.2429 (±3.56)<br>1.4394 (±2.35) |  |
| Ours                               | <b>0.3793</b> (±0.29)                              | $0.0409 (\pm 0.04)$                                                                                          | $0.0241 (\pm 0.01)$ | <b>0.0818</b> (±0.03)    | 142.6949 (±166.90)                                                  | <b>0.0921</b> (±0.07)                              |  |

(b) **Mechanical Property Estimates** of our method significantly outperform the baselines on all metrics. Pervoxel error rate is first computed per object, then averaged across all objects in the test set to avoid weighing some objects more. Global voxel-level normalization yields similar results, see Supplement Tb. 4.

| Method               | ALDE (↓)       | ADE (↓)         | ARE (↓)               | MnRE (↑)              |
|----------------------|----------------|-----------------|-----------------------|-----------------------|
| NeRF2Physics<br>PUGS | 0.736<br>0.661 | 12.725<br>9.461 | 1.040<br><b>0.767</b> | 0.564<br><b>0.576</b> |
| Phys4DGen*           | 0.664          | 9.961           | 0.825                 | 0.566                 |
| Ours                 | 0.631          | 8.433           | 0.887                 | 0.576                 |

(c) **Mass Estimate:** We show the errors for estimating mass of objects on the ABO-500 (Collins et al., 2022) dataset, the only existing benchmark, approximating the accuracy of our  $\rho$  estimates.

| Method       | $\log(E)(\downarrow)$ | $\nu(\downarrow)$   | $\rho(\downarrow)$    |
|--------------|-----------------------|---------------------|-----------------------|
| NeRF2Physics | 1.62 (±4.96)          | _                   | 19.75 (±46.60)        |
| PUGS         | $1.87 (\pm 4.50)$     | _                   | 13.24 (±12.63)        |
| Phys4DGen*   | $1.77 (\pm 8.53)$     | $0.85 \pm 0.01$     | $39.49 \ (\pm 35.47)$ |
| Pixie        | $11.90 \ (\pm 17.41)$ | $3.46 (\pm 4.42)$   | $46.58 \ (\pm 36.35)$ |
| Ours         | <b>0.29</b> (±1.23)   | <b>0.00</b> (±0.00) | <b>11.75</b> (±4.02)  |

(d) **Material Validity:** We report mean values and relative errors (in %) with the closest physically measured material range in MTD (§5.1).

Figure 6: **Quantitative Results and Comparisons:** We compare our method against prior art NeRF2Physics (Zhai et al., 2024), PUGS (Shuai et al., 2025) and Phys4DGen (Lin et al., 2025a), and include limited early results comparing with concurrent method Pixie (Le et al., 2025).

that our method significantly outperforms prior art in accuracy and speed, lowering the barrier for integrating accurate physics into digital workflows across 3D representations, with potential impact across digital twins, robotics, and beyond.

While we show important advances over existing works, our method is not without limitations, which we hope will open exciting avenues of future research. Due to fixed-grid voxelization, our output resolution is limited, causing oversmoothing in highly heterogeneous regions, and may result in approximation errors when transferring results to more detailed input geometry. During annotation, we assume part-level materials are isotropic, which is not a true assumption for some common materials like wood. Further, future work could extend our method to predict additional properties like yield strength, shear modulus and thermal expansion, or to adapt true material properties output by our method to simulator-specific scales required for faster algorithms or implementations. We hope to support future directions in this area by releasing our material estimation benchmark, and trained models.

<span id="page-9-0"></span>![](_page_9_Figure_1.jpeg)

(b) Decoding latent samples leads to plausible (E, ν, ρ) values within real-world materials.

(d) Interpolating in latent space results in valid intermediate materials, unlike naive (E, ν, ρ) interpolation.

Figure 7: Material Latent Space learned by MatVAE ([§3\)](#page-3-0) ensures faithful (a), valid (b), smoothly varying (c), and interpolatable (d) materials. "Invalid" values (c) fall outside all material ranges in MTD ([§5.1\)](#page-5-3).

### ACKNOWLEDGMENTS

We thank Gilles Daviet for help in setting up some of the simulations. We thank Jean-Francois Lafleche for help with rendering. We thank Beau Perschall for help in using the datasets.

##