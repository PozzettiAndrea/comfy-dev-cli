# UniDepthV2:

# <span id="page-0-1"></span>Universal Monocular Metric Depth Estimation Made Simpler

Luigi Piccinelli, Christos Sakaridis, Yung-Hsu Yang, Mattia Segu, Siyuan Li, Wim Abbeloos, and Luc Van Gool

*Abstract*—Accurate monocular metric depth estimation (MMDE) is crucial to solving downstream tasks in 3D perception and modeling. However, the remarkable accuracy of recent MMDE methods is confined to their training domains. These methods fail to generalize to unseen domains even in the presence of moderate domain gaps, which hinders their practical applicability. We propose a new model, UniDepthV2, capable of reconstructing metric 3D scenes from solely single images across domains. Departing from the existing MMDE paradigm, UniDepthV2 directly predicts metric 3D points from the input image at inference time without any additional information, striving for a universal and flexible MMDE solution. In particular, UniDepthV2 implements a self-promptable camera module predicting a dense camera representation to condition depth features. Our model exploits a pseudo-spherical output representation, which disentangles the camera and depth representations. In addition, we propose a geometric invariance loss that promotes the invariance of cameraprompted depth features. UniDepthV2 improves its predecessor UniDepth model via a new edge-guided loss which enhances the localization and sharpness of edges in the metric depth outputs, a revisited, simplified and more efficient architectural design, and an additional uncertainty-level output which enables downstream tasks requiring confidence. Thorough evaluations on ten depth datasets in a zero-shot regime consistently demonstrate the superior performance and generalization of UniDepthV2. Code and models are available at: [github.com/lpiccinelli-eth/UniDepth.](https://github.com/lpiccinelli-eth/unidepth)

*Index Terms*—Depth estimation, 3D estimation, camera prediction, geometric perception, foundation model.

## I. INTRODUCTION

P RECISE pixel-wise depth estimation is crucial to understanding the geometric scene structure, with applications in 3D modeling [\[1\]](#page-10-0), robotics [\[2\]](#page-10-1), [\[3\]](#page-11-0), and autonomous vehicles [\[4\]](#page-11-1), [\[5\]](#page-11-2). However, delivering reliable metric scaled depth outputs is necessary to perform 3D reconstruction effectively, thus motivating the challenging and inherently ill-posed task of Monocular Metric Depth Estimation (MMDE).

While existing MMDE methods [\[6\]](#page-11-3)–[\[12\]](#page-11-4) have demonstrated remarkable accuracy across different benchmarks, they require training and testing on datasets with similar camera intrinsics and scene scales. Moreover, the training datasets typically have a limited size and contain little diversity in scenes and cameras. These characteristics result in poor generalization to real-world inference scenarios [\[13\]](#page-11-5), where images are captured in uncontrolled, arbitrarily structured environments and cameras

![](_page_0_Picture_12.jpeg)

1

<span id="page-0-0"></span>Fig. 1. We introduce UniDepthV2, a novel approach that directly predicts 3D points in a scene with only one image as input. UniDepthV2 incorporates a camera self-prompting mechanism and leverages a spherical 3D output space defined by azimuth and elevation angles, and depth(θ, ϕ, z). This design effectively separates camera and depth optimization by avoiding gradient flowing to the camera module due to depth-related error (εz) compared to the standard Cartesian representation.

with arbitrary intrinsics. What makes the situation even worse is the imperfect nature of actual ground-truth depth which is used to supervise MMDE models, namely its sparsity and its incompleteness near edges, which results in blurry predictions with inaccurate fine-grained geometric details.

Only a few methods [\[14\]](#page-11-6)–[\[16\]](#page-11-7) have addressed the challenging task of generalizable MMDE. However, these methods assume controlled setups at test time, including camera intrinsics. While this assumption simplifies the task, it has two notable drawbacks. Firstly, it does not address the full application spectrum, *e*.*g*. in-the-wild video processing and crowd-sourced image analysis. Secondly, the inherent camera parameter noise is directly injected into the model, leading to large inaccuracies in the high-noise case.

In this work, we address the more demanding task of generalizable MMDE *without* any reliance on additional external information, such as camera parameters, thus defining the universal MMDE task. Our approach, named UniDepthV2, extends UniDepth [\[17\]](#page-11-8) and is the first that attempts to solve this challenging task without restrictions on scene composition and setup and distinguishes itself through its general and adaptable nature. Unlike existing methods, UniDepthV2 delivers metric 3D predictions for any scene *solely* from a single image, waiving the need for extra information about scene or camera. Furthermore, UniDepthV2 flexibly allows for the incorporation of additional camera information at test time. Simultaneously, UniDepthV2 achieves sharper depth predictions with betterlocalized depth discontinuities than the original UniDepth model thanks to a novel edge-guided loss that enhances the

L. Piccinelli, C. Sakaridis, Y-H.. Yang, M. Segu, and S. Li are with ETH Zurich, Switzerland. ¨

W. Abbeloos is with Toyota Motor Europe, Belgium.

L. Van Gool is with ETH Zurich, Switzerland, and with INSAIT, Sofia ¨ University, Bulgaria.

<span id="page-1-0"></span>consistency of the local structure of depth predictions around edges with the respective structure in the ground truth.

The design of UniDepthV2 introduces a camera module that outputs a non-parametric, *i*.*e*. dense camera representation, serving as the prompt to the depth module. However, relying only on this single additional module clearly results in challenges related to training stability and scale ambiguity. We propose an effective pseudo-spherical representation of the output space to disentangle the camera and depth dimensions of this space. This representation employs azimuth and elevation angle components for the camera and a radial component for the depth, forming a perfect orthogonal space between the camera plane and the depth axis. Moreover, the pinhole-based camera representation is positionally encoded via a sine encoding in UniDepthV2, leading to a substantially more efficient computation compared to the spherical harmonic encoding of the pinhole-based representation of the original UniDepth. Figure [1](#page-0-0) depicts our camera self-prompting mechanism and the output space. Additionally, we introduce a geometric invariance loss to enhance the robustness of depth estimation. The underlying idea is that the camera-conditioned depth outputs from two views of the same image should exhibit reciprocal consistency. In particular, we sample two geometric augmentations, creating different views for each training image, thus simulating different apparent cameras for the original scene. Besides the aforementioned consistency-oriented invariance loss, UniDepthV2 features an additional uncertainty output and respective loss. These pixellevel uncertainties are supervised with the differences between the respective depth predictions and their corresponding groundtruth values, and enable the utilization of our MMDE model in downstream tasks such as control which require confidenceaware perception inputs [\[18\]](#page-11-9)–[\[21\]](#page-11-10) for certifiability.

The overall contributions of the present, extended journal version of our work are the first universal MMDE methods, the original UniDepth and the newer UniDepthV2, which predict a point in metric 3D space for each pixel without *any* input other than a single image. An earlier version of this work has appeared in the Conference on Computer Vision and Pattern Recognition [\[17\]](#page-11-8) and has introduced our original UniDepth model. In [\[17\]](#page-11-8), we have first designed a promptable camera module, an architectural component that learns a dense camera representation and allows for non-parametric camera conditioning. Second, we have proposed a pseudo-spherical representation of the output space, thus solving the intertwined nature of camera and depth prediction. In addition, we have introduced a geometric invariance loss to disentangle the camera information from the underlying 3D geometry of the scene. Moreover, in the conference version, we have extensively evaluated and compared UniDepth on ten different datasets in a fair and comparable zero-shot setup to lay the ground for our novel generalized MMDE task. Owing to its design, UniDepth consistently set the state of the art even compared with nonzero-shot methods, ranking first at the time of its appearance in the competitive official KITTI Depth Prediction Benchmark. Compared to the aforementioned conference version, this article makes the following additional contributions:

1) A revisited architectural design of the camera-conditioned monocular metric depth estimator network, which makes UniDepthV2 simpler, substantially more efficient in computation time and parameters, and at the same time more accurate than UniDepth. This design upgrade pertains to the simplification of the connections between the Camera Module and the Depth Module of the network, the more economic sinusoidal embedding of the pinhole-based dense camera representations fed to the Depth Module that we newly adopt, the inclusion of multi-resolution features and convolutional layers in our depth decoder, and the application of the geometric invariance loss solely on output-space features.

- 2) A novel edge-guided scale-shift-invariant loss, which is computed from the predicted and ground-truth depth maps around geometric edges of the input, encourages UniDepthV2 to preserve the local structure of the depth map better, and thus enhances the sharpness of depth outputs substantially compared to UniDepth even on camera and scene domains which are unseen during training.
- 3) An improved practical training strategy that presents the network with a greater diversity of input image shapes and resolutions within each mini-batch and hence with a larger range of intrinsic parameters of the assumed pinhole camera model, leading to increased robustness to the specific input distribution during inference.
- 4) An additional, uncertainty-level output, which requires no additional supervisory signal during training yet allows to quantify confidence during inference reliably and thus enables downstream applications to geometric perception, *e*.*g*. control, which require confidence-aware depth inputs.

The methodological novelties introduced lead to improved performance, robustness, and efficiency of UniDepthV2 compared to UniDepth across a wide range of camera and scene domains. This is demonstrated through an extensive set of comparisons to the latest state-of-the-art methods as well as ablation studies on 10 depth estimation benchmarks, both in the challenging zero-shot evaluation setting and in the practical supervised finetuning setting. UniDepthV2 sets the overall *new state of the art* in MMDE and ranks first among published methods in the competitive official public KITTI Depth Prediction Benchmark.

# II. RELATED WORK

Metric and Scale-Agnostic Depth Estimation. It is crucial to distinguish Monocular Metric Depth Estimation (MMDE) from scale-agnostic, namely up-to-a-scale, monocular depth estimation. MMDE SotA approaches typically confine training and testing to the same domain. However, challenges arise, such as overfitting to the training scenario, leading to considerable performance drops in the presence of minor domain gaps, often overlooked in benchmarks like NYU-Depthv2 [\[22\]](#page-11-11) (NYU) and KITTI [\[23\]](#page-11-12). On the other hand, scale-agnostic depth methods, pioneered by MiDaS [\[24\]](#page-11-13), OmniData [\[25\]](#page-11-14), and LeReS [\[26\]](#page-11-15), show robust generalization by training on extensive datasets. The paradigm has been elevated to another level by repurposing depth-conditioned generative methods for RGB to RGB-conditioned depth generative methods [\[27\]](#page-11-16) or largescale semi-supervised pre-training as in the DepthAnything series [\[28\]](#page-11-17), [\[29\]](#page-11-18). In particular, these two paradigms have been

<span id="page-2-3"></span>![](_page_2_Figure_1.jpeg)

<span id="page-2-1"></span>Fig. 2. **Model Architecture.** UniDepthV2 utilizes solely the input image to generate the 3D output (**O**). It bootstraps a dense camera prediction (**C**) from the Camera Module, injecting prior knowledge on scene scale into the Depth Module via a cross-attention layer per resolution, with 4 layers in total. The camera representation corresponds to azimuth and elevation angles. The geometric invariance loss ( $\mathcal{L}_{con}$ ) enforces consistency between geometric camera-aware output tensors from different geometric augmentations ( $\mathcal{T}_1$ ,  $\mathcal{T}_2$ ). The depth output ( $\mathbf{Z}_{log}$ ) is obtained through an FPN-based decoder that gradually upsamples the feature maps and injects multi-resolution information. The final output is the concatenation of the camera and depth tensors ( $\mathbf{C}||\mathbf{Z}_{log}|$ ), creating two independent optimization spaces for  $\mathcal{L}_{\lambda MSE}$ . The depth output is supervised with the proposed Edge-guided Normalized L1-loss  $\mathcal{L}_{EG-SSI}$ . In addition, UniDepthV2 computes a prediction uncertainty ( $\mathbf{\Sigma}$ ) which is supervised with an L1-loss on the error in log space between predicted and ground-truth depth.

used extensively for other dense prediction tasks, such as segmentation [30] and surface normal estimation [31], [32], and for other modalities, notably video [33], [34]. The limitation of all these methods lies in the absence of a metric output, hindering practical usage in downstream applications.

Monocular Metric Depth Estimation. The introduction of end-to-end trainable neural networks in MMDE, pioneered by [6], marked a significant milestone, also introducing the optimization process through the Scale-Invariant log loss (SI<sub>log</sub>). Subsequent developments witnessed the emergence of advanced networks, ranging from convolution-based architectures [7], [10], [35], [36] to transformer-based approaches [8], [11], [12], [37], [38]. Despite impressive achievements on established benchmarks, MMDE models face challenges in zero-shot scenarios, revealing the need for robust generalization against appearance and geometry domain shifts.

General Monocular Metric Depth Estimation. Recent efforts focus on developing MMDE models [14], [15], [39] for general depth prediction across diverse domains. These models often leverage camera awareness, either by directly incorporating external camera parameters into computations [15], [40] or by normalizing the shape or output depth based on intrinsic properties, as seen in [14], [16], [41], [42]. A new paradigm recently emerged [17], [43], [44], where the goal is to directly estimate the 3D scene from the input image without any additional information other than the RGB input. Our approach fits in the latter new paradigm, namely universal MMDE: we do not require any additional prior information at test time, such as access to camera information.

**Depth Estimation under Challenging Conditions.** A parallel line of work targets robustness when image formation departs from the Lambertian, well-lit assumption. Diffusion-augmented training and guidance improve performance in rare or adverse conditions (*e.g.* night, fog, rain, low light) [45], while dedicated training/evaluation protocols formalize the "challenging conditions" setting and report consistent gains across

benchmarks [46]. For non-Lambertian materials, methods tailored to transparent and mirror surfaces mitigate severe failure modes [47], [48]. Our work is complementary: we pursue universal MMDE, aiming for a single camera-free model that generalizes across such conditions through large-scale training.

#### III. UNIDEPTHV2

<span id="page-2-2"></span>Most of the SotA MMDE methods typically assume access to the camera intrinsics, thus blurring the line between pure depth estimation and actual 3D estimation. In contrast, UniDepthV2 aims to create a universal MMDE model deployable in diverse scenarios without relying on any other external information, such as camera intrinsics, thus leading to 3D-space estimation by design. However, attempting to directly predict 3D points from a single image without a proper internal representation neglects geometric prior knowledge, *i.e.* perspective geometry, burdening the learning process with re-learning laws of perspective projection from data.

Sec. III-A introduces a pseudo-spherical representation of the output space to inherently disentangle camera rays' angles from depth. In addition, our preliminary studies indicate that depth prediction benefits from prior information on the acquisition sensor, leading to the introduction of a self-prompting camera operation in Sec. III-B. Further disentanglement at the level of depth prediction is achieved through a geometric invariance loss, outlined in Sec. III-C. This loss ensures depth predictions remain invariant when conditioned on the bootstrapped camera predictions, promoting robust camera-aware depth predictions. Furthermore, the spatial resolution is enhanced via an edgeguided normalized loss on the depth prediction that forces the network to learn both sharp transitions in depth values and flat surfaces. The overall architecture and the resulting optimization induced by the combination of design choices are detailed in Sec. III-E.

#### <span id="page-2-0"></span>A. 3D Representation

The general-purpose nature of our MMDE method requires inferring both depth and camera intrinsics to make 3D predic-

tions based only on imagery observations. We design the 3D output space presenting a natural disentanglement of the two sub-tasks, namely depth estimation and camera calibration. In particular, we exploit the pseudo-spherical representation where the basis is defined by azimuth, elevation, and log-depth, *i.e.*  $(\theta,\phi,z_{\log})$ , in contrast to the Cartesian representation (x,y,z). The strength of the proposed pseudo-spherical representation lies in the decoupling of camera  $(\theta,\phi)$  and depth  $(z_{\log})$  components, ensuring their orthogonality by design, in contrast to the entanglement present in Cartesian representation.

It is worth highlighting that in this output space, the nonparametric dense representation of the camera is mathematically represented as a tensor  $\mathbf{C} \in \mathbb{R}^{H \times W \times 2}$ , where H and W are the height and width of the input image and the last dimension corresponds to azimuth and elevation values. While in the typical Cartesian space, the backprojection involves the multiplication of homogeneous camera rays and depth, the backprojection operation in the proposed representation space accounts for the concatenation of camera and depth representations. The pencil of rays are defined as  $(\mathbf{r}_1, \mathbf{r}_2, \mathbf{r}_3) = \mathbf{K}^{-1}[\mathbf{u}, \mathbf{v}, \mathbf{1}]^T$ , where  $\mathbf{K}$ is the calibration matrix,  $\mathbf{u}$  and  $\mathbf{v}$  are pixel positions in pixel coordinates, and 1 is a vector of ones. Therefore, the homogeneous camera rays  $(\mathbf{r}_x, \mathbf{r}_y)$  correspond to  $(\frac{\mathbf{r}_1}{\mathbf{r}_2}, \frac{\mathbf{r}_2}{\mathbf{r}_2})$ . Moreover, this dense camera representation can be embedded via a standard Sine encoding, where the total amount of harmonics is 64 per homogeneous ray dimension, namely 128 channels in total.

#### <span id="page-3-0"></span>B. Self-Promptable Camera

The camera module plays a crucial role in the final 3D predictions since its angular dense output accounts for two dimensions of the output space, namely azimuth and elevation. Most importantly, these embeddings prompt the depth module to ensure a bootstrapped prior knowledge of the input scene's global depth scale. The prompting is fundamental to avoid mode collapse in the scene scale and to alleviate the depth module from the burden of predicting depth from scratch as the scale is already modeled by camera output.

Nonetheless, the internal representation of the camera module is based on a pinhole parameterization, namely via focal length  $(f_x, f_y)$  and principal point  $(c_x, c_y)$ . The four tokens conceptually corresponding to the intrinsics are then projected to scalar values, *i.e.*,  $\Delta f_x$ ,  $\Delta f_y$ ,  $\Delta c_x$ ,  $\Delta c_y$ . However, they do not directly represent the camera parameters, but the multiplicative residuals to a pinhole camera initialization, namely  $\frac{H}{2}$  for y-components and  $\frac{W}{2}$  for x-components, leading to  $f_x = \frac{\Delta f_x W}{2}$ ,  $f_y = \frac{\Delta f_y H}{2}$ ,  $c_x = \frac{\Delta c_x W}{2}$ ,  $c_y = \frac{\Delta c_y H}{2}$ , leading to invariance towards input image sizes.

Subsequently, a backprojection operation based on the intrinsic parameters is applied to every pixel coordinate to produce the corresponding rays. The rays are normalized and thus represent vectors on a unit sphere. The critical step involves extracting azimuth and elevation from the backprojected rays, effectively creating a "dense" angular camera representation. This dense representation undergoes Sine encoding to produce the embeddings E. The embedded representations are then seamlessly passed to the depth module as a prompt, where they play a vital role as a conditioning factor. The conditioning is enforced via a cross-attention layer between the projected encoder

feature maps  $\{\mathcal{F}_i\}_{i=1}^4$ , with  $\mathbf{F}_i \in \mathbb{R}^{h \times w \times C}$  and the camera embeddings  $\mathbf{E}$  where (h,w) = (H/14,W/14). The camera-prompted depth features  $\mathbf{F}_i | \mathbf{E} \in \mathbb{R}^{h \times w \times C}$  are defined as

$$\mathbf{F}_i|\mathbf{E} = \mathrm{MLP}(\mathrm{CA}(\mathbf{F}_i, \mathbf{E})),\tag{1}$$

where CA is a cross-attention block and MLP is a MultiLayer Perceptron with one 4C-channel hidden layer.

## <span id="page-3-1"></span>C. Geometric Invariance Loss

The spatial locations from the same scene captured by different cameras should correspond when the depth module is conditioned on the specific camera. To this end, we propose a geometric invariance loss to enforce the consistency of camera-prompted depth features of the same scene from different acquisition sensors. In particular, consistency is enforced on features extracted from identical 3D locations.

For each image, we perform N distinct geometrical augmentations, denoted as  $\{\mathcal{T}_i\}_{i=1}^N$ , with N=2 in our experiments. This operation involves sampling a rescaling factor  $r \sim 2^{\mathcal{U}_{[-2,2]}}$  and a relative translation  $t \sim \mathcal{U}_{[-0.1,0.1]}$ , then cropping it to the current step randomly selected input shape. This is analogous to sampling a pair of images from the same scene and extrinsic parameters but captured by different cameras. Let  $\mathbf{C}_i$  and  $\mathbf{Z}_i$  describe the predicted camera representation and camera-aware depth output, respectively, corresponding to augmentation  $\mathcal{T}_i$ . It is evident that the camera representations differ when two diverse geometric augmentations are applied, i.e.,  $\mathbf{C}_i \neq \mathbf{C}_j$  if  $\mathcal{T}_i \neq \mathcal{T}_j$ . Therefore, the geometric invariance loss can be expressed as

$$\mathcal{L}_{\text{con}}(\mathbf{Z}_1, \mathbf{Z}_2) = \|\mathcal{T}_2 \circ \mathcal{T}_1^{-1} \circ (\mathbf{Z}_1) - \operatorname{sg}(\mathbf{Z}_2)\|_1, \qquad (2)$$

where  $\mathbf{Z}_i$  represents the depth output after being conditioned by camera prompt  $\mathbf{E}_i$ , as outlined in Sec. III-B, and decoded;  $\mathrm{sg}(\cdot)$  corresponds to the stop-gradient detach operation needed to exploit  $\mathbf{Z}_2$  as pseudo ground truth (GT). The bidirectional loss can be computed as:  $\frac{1}{2}(\mathcal{L}_{\mathrm{con}}(\mathbf{Z}_1,\mathbf{Z}_2) + \mathcal{L}_{\mathrm{con}}(\mathbf{Z}_2,\mathbf{Z}_1))$ . It is necessary to apply the geometric invariance loss on the components that are camera-aware, such as the output depth map. Otherwise, the loss would enforce consistency across features that carry camera information purposely different.

#### <span id="page-3-2"></span>D. Edge-Guided Normalized Loss

Modern depth estimation methods must balance global scene understanding with local geometric precision. While UniDepth excels at the former, it lacks accuracy in local, fine-grained details of the geometry of the depicted scenes. To address this, UniDepthV2 involves a novel loss function, named Edge-Guided Scale-Shift Invariant Loss ( $\mathcal{L}_{\rm EG-SSI}$ ), which is explicitly designed to enhance local precision. This loss is computed over image patches extracted from regions where the RGB spatial gradient ranks in the top 5%-quantile, capturing high-contrast areas likely to contain depth discontinuities. Patch sizes are randomly sampled between 4% and 8% of the input image's smallest dimension. By concentrating on these visually salient regions, our model learns to distinguish between genuine geometric discontinuities and misleading high-frequency textures that do not correspond to actual depth changes. The

<span id="page-4-1"></span>loss oversamples high RGB-gradient regions so that thin, high-frequency boundaries are well represented. We do not use superpixels (e.g. SLIC [49]) because their emphasis on region uniformity suppresses thin structures and creates a non-maximum-suppression-like effect that harms boundary detail. For instance, structured patterns such as checkerboard textures or repetitive details on flat surfaces can falsely suggest depth variations, leading to hallucinated discontinuities.

Our approach discourages such errors by enforcing local consistency between the predicted and ground-truth depth. At each selected patch location, we apply a local normalization step where both the predicted depth and ground-truth depth are independently aligned in scale and shift based on the patch's statistics. This ensures that the loss directly measures shape consistency rather than absolute depth values, making it robust to variations in depth scale across different scenes. Specifically, our loss function is formulated as:

$$\mathcal{L}_{\mathrm{EG-SSI}}(\mathbf{D}, \mathbf{D}^*, \Omega) = \sum_{\omega \in \Omega} ||\mathcal{N}_{\omega}(\mathbf{D}_{\omega}) - \mathcal{N}_{\omega}(\mathbf{D}_{\omega}^*)||_{1}, \quad (3)$$

where  $\mathbf{D}$  and  $\mathbf{D}^*$  are the predicted and ground-truth inverse depth,  $\Omega$  is the set of extracted RGB patches, and  $\mathbf{D}_{\omega}$  represents depth values within patch  $\omega$ . The function  $\mathcal{N}_{\omega}(\cdot)$  denotes the standardization operation via subtracting the median and dividing by the mean absolute deviation (MAD) over the patch  $\omega$ . A key advantage of this formulation is that it penalizes two distinct failure cases: (i) regions where the model ignores strong chromatic cues, failing to capture a true depth discontinuity, and (ii) regions where the model incorrectly exploits changes solely in appearance, hallucinating depth discontinuities that do not correspond to actual geometric edges. Since random patch extraction is computationally inefficient in standard ML frameworks such as PyTorch, we implement a custom CUDA kernel, accelerating loss computation by 20x.

## <span id="page-4-0"></span>E. Network Design

**Architecture.** Our network, described in Fig. 2, comprises an Encoder Backbone, a Camera Module, and a Depth Module. The encoder is ViT-based [50], producing features at four different "scales", *i.e.*  $\{\mathbf{F}_i\}_{i=1}^4$ , with  $\mathbf{F}_i \in \mathbb{R}^{h \times w \times C}$ , where  $(h,w)=(\frac{H}{14},\frac{W}{14})$ .

The four Camera Module parameters are initialized as class tokens present in ViT-style backbones. After this initialization, they are (i) processed via 2 layers of self-attention to obtain the corresponding pinhole parameters which are used to produce the final dense representation C as detailed in Sec. III-B, and (ii) further embedded to E via a Sine encoding.

The Depth Module is fed with the four feature maps  $\{\mathbf{F}_i\}_{i=1}^4$  from the encoder. Each feature map  $\mathbf{F}_i$  is conditioned on the camera prompts  $\mathbf{E}$  to obtain  $\mathbf{D}|\mathbf{E}$  as described in Sec. III-B with a different cross-attention layer. The four feature maps are then processed with an FPN-style decoder where the "lateral" convolution is transposed convolution to match the ViT resolution to the resolution of the different layers of the FPN. The log-depth prediction  $\mathbf{Z}_{\log} \in \mathbb{R}^{H \times W \times 1}$  corresponds to the last FPN feature map which is upsampled to the original input shape and processed with two convolutional layers. The final

3D output  $\mathbf{O} \in \mathbb{R}^{H \times W \times 3}$  is the concatenation of predicted rays and depth,  $\mathbf{O} = \mathbf{C} || \mathbf{Z}$ , with  $\mathbf{Z}$  as element-wise exponentiation of  $\mathbf{Z}_{\log}$ . Owing to the architecture's modularity, the ray bundle  $\mathbf{C}$  need not come from UniDepthV2's Camera Module: at inference, it can be injected from any camera model with known parameters and a specified unprojection operator.

**Optimization.** The optimization process is guided by a reformulation of the Mean Squared Error (MSE) loss in the final 3D output space  $(\theta, \phi, z_{\log})$  from Sec. III-A as:

$$\mathcal{L}_{\lambda \text{MSE}}(\boldsymbol{\varepsilon}) = \|\mathbb{V}[\boldsymbol{\varepsilon}]\|_1 + \boldsymbol{\lambda}^T (\mathbb{E}[\boldsymbol{\varepsilon}] \odot \mathbb{E}[\boldsymbol{\varepsilon}]), \tag{4}$$

where  $\boldsymbol{\varepsilon} = \hat{\mathbf{o}} - \mathbf{o}^* \in \mathbb{R}^3$ ,  $\hat{\mathbf{o}} = (\hat{\theta}, \hat{\phi}, \hat{z}_{\log})$  is the predicted 3D output,  $\mathbf{o}^* = (\theta^*, \phi^*, z_{\text{log}}^*)$  is the GT 3D value, and  $\lambda = 0$  $(\lambda_{\theta}, \lambda_{\phi}, \lambda_{z}) \in \mathbb{R}^{3}$  is a vector of weights for each dimension of the output.  $\mathbb{V}[\varepsilon]$  and  $\mathbb{E}[\varepsilon]$  are computed as the vectors of empirical variances and means for each of the three output dimensions over all pixels, *i.e.*  $\{\varepsilon^i\}_{i=1}^N$ . Note that if  $\lambda_d = 1$  for a dimension d, the loss represents the standard MSE loss for that dimension. If  $\lambda_d < 1$ , a scale-invariant loss term is added to that dimension if it is expressed in log space, e.g. for the depth dimension  $z_{\log}$ , or a shift-invariant loss term is added if that output is expressed in linear space. In particular, if only the last output dimension is considered, i.e. the one corresponding to depth, and  $\lambda_z = 0.15$  is utilized, the corresponding loss is the standard  $SI_{log}$ . In our experiments, we set  $\lambda_{\theta} = \lambda_{\phi} = 1$ and  $\lambda_z = 0.15$ . In addition, we extended the optimization with the supervision for the uncertainty prediction  $\Sigma$ , defined as an L1 loss between the predicted uncertainty and the detached error in log space between predicted depth ( $\mathbf{Z}_{\mathrm{log}}$ ) and GT depth  $(\mathbf{Z}_{\log}^*)$ . More formally,

$$\mathcal{L}_{L1} = \|\mathbf{\Sigma} - \operatorname{sg}(|\mathbf{Z}_{\log} - \mathbf{Z}_{\log}^*|)\|_1, \tag{5}$$

with  $sg(\cdot)$  referring to the stop gradient operation. Therefore, the final optimization loss is defined as

$$\mathcal{L} = \mathcal{L}_{\lambda \text{MSE}} + \alpha \mathcal{L}_{\text{con}} + \beta \mathcal{L}_{\text{EG-SSI}} + \gamma \mathcal{L}_{\text{L1}},$$
with  $(\alpha, \beta, \gamma) = (0.1, 1.0, 0.1)$ . (6)

The loss defined here serves as a motivation for the designed output representation. Specifically, employing a Cartesian representation and applying the loss directly to the output space would result in backpropagation through (x, y), and  $z_{log}$  errors. However, x and y components are derived as  $r_x \cdot z$  and  $r_y \cdot z$ as detailed in Sec. III-A. Consequently, the gradients of camera components, expressed by  $(r_x, r_y)$ , and of depth become intertwined, leading to suboptimal optimization as discussed in Sec. IV-C. Depth estimators often entangle image shape with scene scale by implicitly encoding aspects of the camera parameters within the image dimensions [14]. This reliance on fixed input shapes can limit their ability to generalize across different image resolutions and aspect ratios. In contrast, UniDepthV2 is designed to be robust to variations in image shape, ensuring that the predicted scene geometry and camera FoV remain consistent regardless of input resolution. This flexibility allows the model to adapt to different computational constraints, striking a balance between finer detail and processing speed while maintaining global scene accuracy. To achieve this robustness, we train on dynamically varying image shapes and resolutions, ensuring that the model learns to infer depth consistently across

<span id="page-5-1"></span>![](_page_5_Figure_1.jpeg)

Fig. 3. Zero-shot qualitative results. Each pair of consecutive rows corresponds to one test sample. Each odd row shows the input RGB image and the 2D error map color-coded with *coolwarm* based on the absolute relative error. Each even row shows GT depth and the predicted point cloud. The last column represents the specific colormap ranges for depth and error. (†): DDAD domain in the training set.

a wide range of input conditions. Specifically, we sample images with variable pixel counts between 0.2MP and 0.6MP, allowing the model to operate effectively across diverse resolutions without being biased toward a single fixed input size.

## IV. EXPERIMENTS

## <span id="page-5-0"></span>*A. Experimental Setup*

Data. The training data is the combination of 23 publicly available datasets: A2D2 [\[52\]](#page-12-6), Argoverse2 [\[53\]](#page-12-7), ARKit-Scenes [\[54\]](#page-12-8), BEDLAM [\[55\]](#page-12-9), BlendedMVS [\[56\]](#page-12-10), DL3DV [\[57\]](#page-12-11), DrivingStereo [\[58\]](#page-12-12), DynamicReplica [\[59\]](#page-12-13), EDEN [\[60\]](#page-12-14), HOI4D [\[61\]](#page-12-15), HM3D [\[62\]](#page-12-16), Matterport3D [\[63\]](#page-12-17), Mapillary-PSD [\[42\]](#page-11-36), MatrixCity [\[64\]](#page-12-18), MegaDepth [\[65\]](#page-12-19), NianticMapFree [\[66\]](#page-12-20), PointOdyssey [\[67\]](#page-12-21), ScanNet [\[68\]](#page-12-22), Scan-Net++ [\[69\]](#page-12-23), TartanAir [\[70\]](#page-12-24), Taskonomy [\[71\]](#page-12-25), Waymo [\[72\]](#page-12-26), and WildRGBD [\[73\]](#page-12-27) for a total of 16M images. We evaluate

the generalizability of models by testing them on ten datasets not seen during training, grouped in different domains that are defined based on indoor, outdoor or "challenging" settings. The indoor group corresponds to the validation splits of SUN-RGBD [\[74\]](#page-12-28), IBims [\[75\]](#page-12-29), and TUM-RGBD [\[76\]](#page-12-30), the outdoor group comprises ETH3D [\[77\]](#page-12-31), Sintel [\[78\]](#page-12-32), DDAD [\[79\]](#page-12-33), and NuScenes [\[80\]](#page-12-34), while the "challenging" domain is composed of HAMMER [\[81\]](#page-13-0), Booster [\[48\]](#page-12-3), and FLSea [\[82\]](#page-13-1).

Evaluation Details. All methods have been re-evaluated with a fair and consistent pipeline. In particular, we do not exploit any test-time augmentations, and we utilize the same weights for all zero-shot evaluations. We use the checkpoint corresponding to the zero-shot model for each method, *i*.*e*. not fine-tuned on KITTI or NYU. The metrics utilized in the main experiments are δ SSI 1 , FA, and ρA. δ<sup>1</sup> measures the depth estimation performance. F<sup>A</sup> is the area under the curve (AUC) of F1-

<span id="page-6-1"></span><span id="page-6-0"></span>TABLE I

RESULTS FOR INDOOR DOMAINS. ALL METHODS ARE TESTED IN A ZERO-SHOT FASHION. MISSING VALUES (-) INDICATE THE MODEL'S INABILITY TO PRODUCE THE RESPECTIVE OUTPUT. †: REQUIRES GROUND-TRUTH (GT) CAMERA FOR 3D RECONSTRUCTION. ‡: REQUIRES GT CAMERA FOR 2D DEPTH MAP INFERENCE.

| Method                        |                     | SUNRO                     | GBD            |                |                     | IBim                      | s-1            |                |                     | TUM-R                     | GBD            |                 |
|-------------------------------|---------------------|---------------------------|----------------|----------------|---------------------|---------------------------|----------------|----------------|---------------------|---------------------------|----------------|-----------------|
| Method                        | $\delta_1 \uparrow$ | $\mathrm{ARel}\downarrow$ | $F_1 \uparrow$ | $\rho\uparrow$ | $\delta_1 \uparrow$ | $\mathrm{ARel}\downarrow$ | $F_1 \uparrow$ | $\rho\uparrow$ | $\delta_1 \uparrow$ | $\mathrm{ARel}\downarrow$ | $F_1 \uparrow$ | $\rho \uparrow$ |
| Metric3D <sup>†‡</sup> [14]   | 1.9                 | 48.7                      | -              | -              | 75.1                | 19.3                      | -              | -              | 7.7                 | 61.1                      | -              | -               |
| Metric3Dv2 <sup>†‡</sup> [16] | 81.2                | 13.3                      | -              | -              | 68.4                | 20.7                      | -              | -              | 63.0                | 9.3                       | -              | -               |
| ZoeDepth <sup>†</sup> [39]    | 80.9                | 13.6                      | -              | -              | 49.8                | 21.5                      | -              | -              | 55.6                | 33.6                      | -              | -               |
| UniDepth [17]                 | 94.3                | 10.4                      | 78.6           | 85.8           | 15.7                | 41.0                      | 30.3           | 76.6           | 72.3                | 17.2                      | 54.8           | 86.8            |
| MASt3R [51]                   | 80.1                | 14.4                      | 71.5           | 92.0           | 61.0                | 19.7                      | 55.7           | 76.0           | 52.4                | 27.9                      | 44.1           | 93.7            |
| DepthPro [43]                 | 83.1                | 13.3                      | 71.1           | 89.3           | 82.3                | 17.0                      | 62.8           | 75.9           | 56.9                | 19.9                      | 48.1           | 96.5            |
| UniDepthV2-Small              | 90.8                | 10.5                      | 74.2           | 87.7           | 86.6                | 13.5                      | 62.4           | 67.5           | 69.0                | 23.6                      | 50.6           | 86.1            |
| UniDepthV2-Base               | 94.4                | <u>8.4</u>                | 79.9           | 91.1           | <u>89.7</u>         | <u>11.1</u>               | 68.5           | 76.5           | <u>77.5</u>         | 20.7                      | 57.3           | 89.4            |
| UniDepthV2-Large              | 96.4                | 6.8                       | 84.6           | <b>93.4</b>    | <b>94.5</b>         | 7.8                       | 70.9           | 74.1           | 90.5                | 22.1                      | 62.9           | 89.6            |

RESULTS FOR OUTDOOR DOMAINS. ALL METHODS ARE TESTED IN A ZERO-SHOT FASHION. MISSING VALUES (-) INDICATE THE MODEL'S INABILITY TO PRODUCE THE RESPECTIVE OUTPUT. †: REQUIRES GROUND-TRUTH (GT) CAMERA FOR 3D RECONSTRUCTION. ‡: REQUIRES GT CAMERA FOR 2D DEPTH MAP INFERENCE. FOR DDAD, METRIC3D AND METRIC3DV2 ARE EXCLUDED FROM EVALUATION AS THEY ARE TRAINED ON IT.

| Method                        |                     | ETH:                      | 3D             |                |                     | Sint              | el             |                | 1                   | DDA                       | D              |                 |                     | NuSce                     | enes           |                |
|-------------------------------|---------------------|---------------------------|----------------|----------------|---------------------|-------------------|----------------|----------------|---------------------|---------------------------|----------------|-----------------|---------------------|---------------------------|----------------|----------------|
| Method                        | $\delta_1 \uparrow$ | $\mathrm{ARel}\downarrow$ | $F_1 \uparrow$ | $\rho\uparrow$ | $\delta_1 \uparrow$ | $ARel \downarrow$ | $F_1 \uparrow$ | $\rho\uparrow$ | $\delta_1 \uparrow$ | $\mathrm{ARel}\downarrow$ | $F_1 \uparrow$ | $\rho \uparrow$ | $\delta_1 \uparrow$ | $\mathrm{ARel}\downarrow$ | $F_1 \uparrow$ | $\rho\uparrow$ |
| Metric3D <sup>†‡</sup> [14]   | 19.7                | 136.8                     | -              | -              | 1.4                 | 105.5             | -              | -              | n/a                 | n/a                       | n/a            | n/a             | 75.4                | 23.7                      | -              | -              |
| Metric3Dv2 <sup>†‡</sup> [16] | 90.0                | 12.7                      | -              | -              | 34.5                | 43.9              | -              | -              | n/a                 | n/a                       | n/a            | n/a             | 84.1                | 23.6                      | -              | -              |
| ZoeDepth <sup>†</sup> [39]    | 33.8                | 54.7                      | -              | -              | 5.6                 | 95.9              | -              | -              | 27.9                | 50.9                      | -              | -               | 33.8                | 42.0                      | -              | -              |
| UniDepth [17]                 | 18.5                | 53.3                      | 27.6           | 42.6           | 13.2                | 124.6             | 40.2           | 65.6           | 85.8                | 12.5                      | 72.8           | 98.1            | 84.6                | 12.7                      | 64.4           | 97.7           |
| MASt3R [51]                   | 21.4                | 45.3                      | 28.4           | 92.2           | 17.2                | 71.6              | 41.5           | 72.2           | 4.3                 | 56.7                      | 22.1           | 74.6            | 2.7                 | 65.6                      | 13.6           | 78.3           |
| DepthPro [43]                 | 39.7                | 65.2                      | 41.2           | 77.4           | 26.2                | 133.4             | 49.7           | 75.2           | 29.9                | 37.3                      | 42.1           | 83.0            | 56.6                | 28.7                      | 46.5           | 79.1           |
| UniDepthV2-Small              | 64.6                | 113.2                     | 44.3           | 78.4           | 14.6                | 107.7             | 37.1           | 73.5           | 83.3                | 16.4                      | 68.5           | 94.7            | 82.1                | 18.3                      | 59.7           | 96.2           |
| UniDepthV2-Base               | 75.4                | 70.1                      | 53.5           | 91.4           | 31.9                | 50.1              | 51.8           | 75.9           | 86.8                | 14.2                      | 71.4           | 96.1            | 85.3                | 16.2                      | 63.6           | 96.6           |
| UniDepthV2-Large              | 85.2                | 16.6                      | 59.3           | 92.6           | 34.4                | 61.0              | 51.4           | 76.3           | 88.2                | 13.8                      | 73.3           | 96.7            | 87.0                | 15.0                      | 66.7           | 97.2           |

score [83] up to 1/20 of the datasets' maximum depth and evaluates 3D estimation accuracy.  $\rho_{\rm A}$  [84], [85] evaluates the camera performance and is the AUC of the average angular error of camera rays up to 15°. We do not use parametric evaluation of *e.g.* focal length, since it is a less flexible metric across diverse camera models and perfectly unrectified images. Moreover, we present the fine-tuning ability of UniDepthV2 by training the final checkpoint on KITTI and NYU-Depth V2 and evaluating in-domain, as per standard practice.

Confidence predictions are evaluated with specific and established metrics such as AUSE [86]  $(w.r.t. \delta_1)$  and its normalized version (nAUSE) and  $Spearman's \rho$ . AUSE ranks pixels by predicted uncertainty, progressively masks the most uncertain fraction, recomputes  $\delta_1$  at each step, and integrates the gap to the oracle curve (ranking by true error). Oracle's AUSE is 0 by definition and nAUSE is AUSE normalized by the random error, i.e. nAUSE = 1 equals random.  $\rho$  is the rank correlation between predicted uncertainty and per-pixel error (1 perfect ordering, 0 no monotonic relation, < 0 inverted). Both metrics therefore assess ranking quality: AUSE under progressive masking and  $\rho$  as a global monotonicity check.

**Implementation Details.** UniDepthV2 is implemented in PyTorch [87] and CUDA [88]. For training, we use the AdamW [89] optimizer ( $\beta_1 = 0.9$ ,  $\beta_2 = 0.999$ ) with an initial learning rate of  $5 \times 10^{-5}$ . The learning rate is divided by a factor of 10 for the backbone weights for every experiment and weight decay is set to 0.1. We exploit Cosine Annealing as learning rate and weight decay scheduler to one-tenth starting

from 30% of the whole training. We run 300k optimization iterations with a batch size of 128. The training time amounts to 6 days on 16 NVIDIA 4090 with half precision. The dataset sampling procedure follows a weighted sampler, where the weight of each dataset is its number of scenes. Our augmentations are both geometric and photometric, i.e. random resizing, cropping, and translation for the former type, and brightness, gamma, saturation, and hue shift for the latter. We randomly sample the image ratio per batch between 2:1 and 1:2. Our ViT [50] backbone is initialized with weights from DINO-pretrained [90] models. We train three models, one for each available ViT backbone, i.e. Small, Base, and Large, corresponding to the UniDepthV2 variants "-Small", "-Base", and "-Large". For the ablations, we run 100k training steps with a ViT-S backbone, with the same training pipeline as for the main experiments. Because the ablation runs use a shorter schedule and a fixed ViT-S backbone, the ablation "final" model is not directly comparable to the main UniDepthV2-Small results in Tabs. I to III.

#### B. Comparison with The State of The Art

We evaluate our method on a total of ten zero-shot validation sets. The domains cover indoor, outdoor, and challenging scenes, e.g. underwater or transparent objects, shown in Tables I to III, respectively. Our model performs better than or at least on par with all baselines, even outperforming methods that require ground-truth camera parameters at inference time, such as [14], [16]. Notably, UniDepthV2 excels in 3D estimation, as reflected in the  $F_A$  metric, where it achieves a consistent

<span id="page-7-3"></span><span id="page-7-0"></span>TABLE III

RESULTS FOR CHALLENGING DOMAINS. ALL METHODS ARE TESTED IN A ZERO-SHOT FASHION. MISSING VALUES (-) INDICATE THE MODEL'S INABILITY
TO PRODUCE THE RESPECTIVE OUTPUT. †: REQUIRES GROUND-TRUTH (GT) CAMERA FOR 3D RECONSTRUCTION. ‡: REQUIRES GT CAMERA FOR 2D

DEPTH MAP INFERENCE.

| Method                        |                     | HAMI             | MER            |                        |                     | Boos                      | ster           |                        |                     | FLS               | ea             |                        |
|-------------------------------|---------------------|------------------|----------------|------------------------|---------------------|---------------------------|----------------|------------------------|---------------------|-------------------|----------------|------------------------|
| Method                        | $\delta_1 \uparrow$ | $ARel\downarrow$ | $F_A \uparrow$ | $\rho_{\rm A}\uparrow$ | $\delta_1 \uparrow$ | $\mathrm{ARel}\downarrow$ | $F_A \uparrow$ | $\rho_{\rm A}\uparrow$ | $\delta_1 \uparrow$ | $ARel \downarrow$ | $F_A \uparrow$ | $\rho_{\rm A}\uparrow$ |
| Metric3D <sup>†‡</sup> [14]   | 0.9                 | 122.5            | -              | -                      | 1.2                 | 201.2                     | -              | -                      | 0.7                 | 117.9             | -              | -                      |
| Metric3Dv2 <sup>†‡</sup> [16] | 65.3                | 21.4             | -              | -                      | 9.1                 | 69.0                      | -              | -                      | 17.5                | 85.7              | -              | -                      |
| ZoeDepth <sup>†</sup> [39]    | 0.9                 | 90.2             | -              | -                      | 28.5                | 52.7                      | -              | -                      | 15.7                | 161.1             | -              | -                      |
| UniDepth [17]                 | 1.8                 | 56.9             | 52.1           | 55.3                   | 42.9                | 34.7                      | 42.7           | 73.7                   | 29.9                | 70.2              | 53.6           | 71.0                   |
| MASt3R [51]                   | 2.2                 | 69.7             | 38.1           | 86.5                   | 37.9                | 46.1                      | 43.9           | 69.6                   | 26.7                | 41.5              | 53.6           | 67.5                   |
| DepthPro [43]                 | 29.4                | 37.5             | 71.0           | 69.1                   | 58.4                | 25.7                      | 11.1           | -                      | 10.6                | 145.2             | 4.0            | 4.7                    |
| UniDepthV2-Small              | 30.6                | 32.1             | 57.0           | 65.6                   | 54.4                | 30.3                      | 48.6           | 70.1                   | 72.3                | 20.6              | 90.5           | 87.2                   |
| UniDepthV2-Base               | 89.7                | 22.4             | 68.5           | 76.5                   | <u>62.1</u>         | 24.4                      | 55.1           | <b>75.2</b>            | <u>89.1</u>         | 12.2              | 95.3           | 93.1                   |
| UniDepthV2-Large              | 64.5                | 17.5             | 74.9           | 78.3                   | 67.6                | 19.6                      | <b>57</b> .9   | 66.6                   | 90.5                | 12.1              | 95.9           | 92.8                   |

![](_page_7_Figure_3.jpeg)

<span id="page-7-1"></span>Fig. 4. Insensitivity to image shape. UniDepthV2 is trained with a variable input shape pipeline in addition to random resizing for each of the image pairs. The proposed training strategy improves the robustness in terms of predicted depth scale and accuracy  $(\delta_1)$  to the input image's shape compared to two other state-of-the-art methods.

improvement ranging from 0.5% to 18.1% over the secondbest method. Additionally, it outperforms UniDepth [17] in nearly all cases, except for the  $\rho_A$  metric on IBims-1, DDAD, and NuScenes. Moreover, we evaluate and compare inference efficiency in Table VIII. All models are run with the same settings. UniDepthV2 is among the fastest and most efficient, even though it requires an additional module for camera prediction. This demonstrates that our proposed version is a significant step forward in both performance and efficiency. However, the camera parameter estimation ( $\rho_A$ ) sees only marginal improvements, indicating that the limited diversity of training cameras remains a challenge that could be addressed with additional camera-only training, as suggested in [43].

Table V and Table VI show results for models fine-tuned on the NYU and KITTI training sets and evaluated on their respective validation splits, following standard protocols. Fine-tuning performance serves as an indicator of a model's ability to specialize to specific downstream tasks and domains. UniDepthV2 effectively adapts to new domains and outperforms methods with similar capacity that were pre-trained on large, diverse datasets before fine-tuning on NYU or KITTI, such as [16], [29], [39]. This is particularly evident in the outdoor setting (KITTI), as shown in Table VI. As detailed in Section III-E, our training strategy incorporates variable image aspect ratios and

<span id="page-7-2"></span>TABLE IV EDGE EVALUATION. SCALE-INVARIANT BOUNDARY  $F_1$  on ETH3D, IBIMS-1, AND SINTEL FOLLOWING THE PROTOCOL OF [43]. †: INFERENCE PERFORMED AT FIXED RESOLUTION OF  $1536 \times 1536$  INSTEAD OF THE INPUT ORIGINAL.

|                            | or omioni                                                                         | 121          |        |
|----------------------------|-----------------------------------------------------------------------------------|--------------|--------|
| Method                     | ETH3D                                                                             | IBims-1      | Sintel |
| Metric3Dv2 [16]            | 2.86                                                                              | 13.48        | 23.03  |
| ZoeDepth [39]              | 0.75                                                                              | 4.16         | 2.63   |
| UniDepth [17]              | 0.22                                                                              | 2.64         | 0.42   |
| MASt3R [51]                | 0.60                                                                              | 1.45         | 1.08   |
| DepthPro <sup>†</sup> [43] | <b>4.04</b>                                                                       | <b>19.38</b> | 29.24  |
| UniDepthV2-Small           | $   \begin{array}{r}     2.13 \\     \underline{2.99} \\     2.95   \end{array} $ | 10.53        | 20.58  |
| UniDepthV2-Base            |                                                                                   | 12.93        | 28.25  |
| UniDepthV2-Large           |                                                                                   | <u>13.75</u> | 33.08  |

resolutions within the same distributed batch. Combined with camera conditioning and invariance learning, this approach enhances the model's robustness to changes in input image shape. Figure 4 quantifies this effect: the y-axis represents normalized metric accuracy ( $\delta_1$  scaled by the method's maximum value), while the x-axis varies the image shape. The normalization ensures a consistent scale across models. UniDepthV2 is almost invariant to image shape, demonstrating that it can effectively trade off resolution for speed without sacrificing accuracy, as clearly illustrated in Figure 4.

As shown in Figure 5, increasing input resolution causes FPS to drop roughly inversely with resolution, while peak GPU memory grows near-quadratically. UniDepthV2 is around 2× faster than the baselines up to  $\sim$ 2 Megapixel with a comparable memory footprint, but beyond ~5 MP all methods become memory-bound (> 15 GB) and converge to sub-FPS throughput. In practice, GPU memory sets the feasible operating point, motivating our shape-invariant inference that can trade resolution for speed without sacrificing accuracy (Figure 4). Table IV follows protocol from [43], but it is important to note a resolution asymmetry: DepthPro is evaluated at a fixed high input of 1536×1536, whereas other models that are more flexible w.r.t. input, such as UniDepthV2, are run at the native input resolution, which is typically between one-sixth to one-quarter of DepthPro's. Since boundary F1 improves with input resolution, i.e. sharper and less aliased contours lead to higher truepositive matches, DepthPro's scores are inflated by resolution. Even under this stricter setting, UniDepthV2-Large attains the

<span id="page-8-5"></span>![](_page_8_Figure_1.jpeg)

![](_page_8_Figure_2.jpeg)

<span id="page-8-3"></span>Fig. 5. **Impact of resolution on memory and runtime.** Frames-per-second (top) and peak memory (bottom) versus input resolution in Mega Pixels (log-scale). Missing points at 32MP are due to OOM.

<span id="page-8-1"></span>TABLE V

COMPARISON ON NYU VALIDATION SET. ALL MODELS ARE TRAINED ON NYU. THE FIRST 4 ARE TRAINED ONLY ON NYU. THE LAST 4 ARE FINE-TUNED ON NYU.

| Method               | $\delta_1$ Hig | $\delta_2$<br>her is be | $\delta_3$ | A.Rel | RMS<br>ower is bet | $\rm Log_{10}$ ter |
|----------------------|----------------|-------------------------|------------|-------|--------------------|--------------------|
| BTS [41]             | 88.5           | 97.8                    | 99.4       | 10.9  | 0.391              | 0.046              |
| AdaBins [8]          | 90.1           | 98.3                    | 99.6       | 10.3  | 0.365              | 0.044              |
| NeWCRF [11]          | 92.1           | 99.1                    | 99.8       | 9.56  | 0.333              | 0.040              |
| iDisc [12]           | 93.8           | 99.2                    | 99.8       | 8.61  | 0.313              | 0.037              |
| ZoeDepth [39]        | 95.2           | 99.5                    | 99.8       | 7.70  | 0.278              | 0.033              |
| Metric3Dv2 [16]      | 98.9           | 99.8                    | 100        | 4.70  | 0.183              | 0.020              |
| DepthAnythingv2 [29] | 98.4           | 99.8                    | 100        | 5.60  | 0.206              | 0.024              |
| UniDepthV2 -Large    | 98.8           | 99.8                    | 100        | 4.68  | 0.180              | 0.020              |

best result on Sintel and remains competitive on ETH3D and IBims-1 and clearly outperforms the original UniDepth.

## <span id="page-8-0"></span>C. Ablation Studies

The importance of each new component introduced in UniDepthV2 in Sec. III is evaluated by ablating the method in Tables IX, X, XI, and XII. All ablations exploit the predicted camera representation, if not stated otherwise. Table IX evaluates the impact of various architectural modifications compared to UniDepth [17], analyzing their effects on both performance and efficiency. Table X assesses the importance of the proposed loss function (Sec. III-D) and examines the effect of applying the geometric invariance loss originally introduced in UniDepth [17] (Sec. III-C) in different spaces. The rationale behind our design choices is to maintain simplicity while maximizing effectiveness. Additionally, in Table XI we analyze the role of camera conditioning and report results for the original UniDepth under the same training and evaluation setup as our method for a direct comparison. The evaluation is based on four key metrics:  $\delta_1$ , which measures metric depth accuracy; SI<sub>log</sub>, which assesses scale-invariant scene geometry; FA, which captures the 3D estimation capability; and  $\rho_{\rm A}$ , which evaluates monocular camera parameter estimation.

TABLE VI

<span id="page-8-2"></span>COMPARISON ON KITTI EIGEN-SPLIT VALIDATION SET. ALL MODELS ARE TRAINED ON KITTI EIGEN-SPLIT TRAINING AND TESTED ON THE CORRESPONDING VALIDATION SPLIT. THE FIRST 4 ARE TRAINED ONLY ON KITTI. THE LAST 4 ARE FINE-TUNED ON KITTI.

| Method               | $\delta_1$ | $\delta_2$ | $\delta_3$ | A.Rel | RMS       | $RMS_{log}$ |
|----------------------|------------|------------|------------|-------|-----------|-------------|
| - Witting            | Hig        | her is be  | tter       | L     | ower is b | etter       |
| BTS [41]             | 96.2       | 99.4       | 99.8       | 5.63  | 2.43      | 0.089       |
| AdaBins [8]          | 96.3       | 99.5       | 99.8       | 5.85  | 2.38      | 0.089       |
| NeWCRF [11]          | 97.5       | 99.7       | 99.9       | 5.20  | 2.07      | 0.078       |
| iDisc [12]           | 97.5       | 99.7       | 99.9       | 5.09  | 2.07      | 0.077       |
| ZoeDepth [39]        | 96.5       | 99.1       | 99.4       | 5.76  | 2.39      | 0.089       |
| Metric3Dv2 [14]      | 98.5       | 99.8       | 100        | 4.40  | 1.99      | 0.064       |
| DepthAnythingv2 [29] | 98.3       | 99.8       | 100        | 4.50  | 1.86      | 0.067       |
| UniDepthV2 -Large    | 98.9       | 99.8       | 99.9       | 3.73  | 1.71      | 0.061       |

#### TABLE VII

<span id="page-8-4"></span>Uncertainty evaluation. "In-domain" uses the validation splits of the training datasets; "Zero-shot" evaluates on unseen datasets. AUSE [86] is the area under the sparsification error curve w.r.t.  $\delta_1$  score, and nAUSE is the normalized version where 0 = oracle, 1 = random.  $\rho$  is the Spearman rank correlation between predicted uncertainty and error.

| Model            |                   | In-domain                  |                 | Zero-shot |                            |                |  |  |
|------------------|-------------------|----------------------------|-----------------|-----------|----------------------------|----------------|--|--|
| Model            | $AUSE \downarrow$ | $\mathrm{nAUSE}\downarrow$ | $\rho \uparrow$ | AUSE ↓    | $\mathrm{nAUSE}\downarrow$ | $\rho\uparrow$ |  |  |
| UniDepthV2-Small | 0.020             | 0.221                      | 0.682           | 0.040     | 0.539                      | 0.289          |  |  |
| UniDepthV2-Base  | 0.018             | 0.212                      | 0.721           | 0.034     | 0.637                      | 0.291          |  |  |
| UniDepthV2-Large | 0.017             | 0.199                      | 0.744           | 0.032     | 0.645                      | 0.299          |  |  |

All reported metrics correspond to the aggregated zero-shot performance across datasets, as detailed in Sec. IV-A.

Table IX outlines the key modifications Architecture. that transform the original UniDepth [17] architecture into UniDepthV2. The first major change is the removal of spherical harmonics (SH)-based encoding, which is computationally inefficient. Instead, we revert to standard Sine encoding (row 2). While the difference in performance is minimal in our setup, we hypothesize that the encoding's impact diminishes as the model benefits from larger and more diverse training data across different cameras. Next, we eliminate the attention mechanism in row 3 due to its high computational cost. This removal results in a significant performance drop, e.g. -4.3% for  $\delta_1$ , but yields a greater than 2x improvement in efficiency. In row 4, we replace the pure MLP-based decoder with ResNet blocks, introducing spatial  $3 \times 3$  convolutions. This modification enhances performance by leveraging local spatial structure while inducing a minimal impact on efficiency. Finally, row 5 integrates a multi-resolution feature fusion from the encoder to the decoder, following an FPN-style design. This final architecture significantly reduces computational cost while preserving overall performance: the final model (row 5) achieves similar performance to the original UniDepth (row 1) while requiring only one-third of the computation. Row 6 reports the full UniDepthV2 configuration, i.e. the architecture from row 5 with training augmented with the proposed losses.

 $\mathcal{L}_{\mathrm{EG-SSI}}$  Loss. The effectiveness of the proposed  $\mathcal{L}_{\mathrm{EG-SSI}}$  loss, detailed in Sec. III-D, is evaluated in row 2 vs. row 3 of Table X. Introducing this loss results in a 4.7% improvement in  $\delta_1$  and a 1.8% improvement in  $F_A$ , demonstrating its contribution to both metric accuracy and 3D estimation. Interestingly, despite  $\mathcal{L}_{\mathrm{EG-SSI}}$  not explicitly supervising camera parameter estimation, the  $\rho_A$  metric also shows improvement. This suggests that the loss contributes to a less noisy training

<span id="page-9-5"></span>![](_page_9_Figure_1.jpeg)

<span id="page-9-4"></span>Fig. 6. Comparisons of predicted edges. Each row displays the input RGB image and the 2D depth maps predicted by compared methods, color-coded with the magma reverse colormap with a range between 0 and 50 meters. Better viewed on a screen and zoomed in.

#### TABLE VIII

<span id="page-9-0"></span>**EFFICIENCY RESULTS.** Inference efficiency results for all methods. Hardware is a A6000 with mixed precision and 0.5 Megapixel images, all methods use a ViT backbone; ViT-Large for competing methods.  $\dagger$ : Inference on native 1536  $\times$  1536 resolution.  $\ddagger$ : ConvNext-L backbone.

| Method                     | Latency (ms) | Params (M) | FLOPS (T) | Memory (GiB) |
|----------------------------|--------------|------------|-----------|--------------|
| Metric3D <sup>‡</sup> [14] | 29.6         | 203.2      | 0.90      | 1.71         |
| Metric3Dv2 [16]            | 133.6        | 411.9      | 3.47      | 3.50         |
| ZoeDepth [39]              | 64.8         | 346.1      | 2.08      | 2.02         |
| UniDepth [17]              | 91.0         | 347.0      | 2.02      | 2.81         |
| MASt3R [51]                | 357.3        | 688.6      | 3.19      | 4.94         |
| DepthPro <sup>†</sup> [43] | 270.6        | 952.0      | 19.3      | 8.42         |
| UniDepthV2-Small           | 23.0         | 34.18      | 0.29      | 0.66         |
| UniDepthV2-Base            | 35.1         | 114.4      | 0.82      | 1.32         |
| UniDepthV2-Large           | 65.4         | 353.8      | 2.17      | 3.47         |

#### TABLE IX

<span id="page-9-1"></span>ARCHITECTURAL ABLATIONS. THE DIFFERENT ARCHITECTURAL ADDITIONS ("+") AND SUBTRACTIONS ("-") FROM THE ORIGINAL UNIDEPTH [17] ARE REPORTED. "- SHE + SINE": CAMERA ENCODING VIA SINE ENCODING INSTEAD OF SPHERICAL HARMONIC TRANSFORM OF THE PINHOLE-BASED PENCIL OF RAYS. "- ATTENTION": ATTENTION LAYERS IN THE DECODER ARE REMOVED. "+ RESNET BLOCKS": THE ATTENTION LAYERS IN THE DECODER ARE SUBSTITUTED WITH SIMPLER RESNET BLOCKS. "+ MULTI-RESOL.": THE DECODER HAS LATERAL CONNECTIONS WITH THE SHALLOWER ENCODER LAYER, RATHER THAN A SIMPLER MERGING OF ALL RESOLUTIONS IN THE BOTTLENECK.

|   | Architecture    |                     | Perforr               | nance          |                             | Effici        | Efficiency  |  |  |  |
|---|-----------------|---------------------|-----------------------|----------------|-----------------------------|---------------|-------------|--|--|--|
|   | Architecture    | $\delta_1 \uparrow$ | $SI_{log} \downarrow$ | $F_A \uparrow$ | $\rho_{\mathrm{A}}\uparrow$ | Latency (ms)↓ | Params (M)↓ |  |  |  |
| 1 | UniDepth [17]   | 54.5                | 16.4                  | 56.1           | 77.1                        | 73.2          | 35.2        |  |  |  |
| 2 | - SHE + Sine    | 54.6                | 16.4                  | 56.0           | 76.9                        | 53.2          | 35.2        |  |  |  |
| 3 | - Attention     | 50.3                | 17.9                  | 51.0           | 76.6                        | 20.4          | 29.0        |  |  |  |
| 4 | + ResNet Blocks | 52.6                | 16.6                  | 55.0           | 76.6                        | 24.0          | 33.5        |  |  |  |
| 5 | + Multi-resol   | 54.5                | 16.3                  | 56.0           | 77.9                        | 25.0          | 34.2        |  |  |  |
| 6 | UniDepthV2      | 60.0                | 15.3                  | 57.9           | 79.8                        | 25.0          | 34.2        |  |  |  |

process, leading to better feature representations in the encoder. A qualitative comparison of the impact of  $\mathcal{L}_{\mathrm{EG-SSI}}$  is presented in Fig. 6. The difference between the third and fourth columns highlights the visual impact of the proposed loss, particularly in refining depth discontinuities. Additionally, the comparison between the second and third columns illustrates the combined effect of architectural changes and increased data diversity, showing improved reconstruction of finer details, such as body parts that were previously smoothed or missed.

 $\mathcal{L}_{\mathrm{con}}$  **Output Space.** UniDepthV2 introduces multiple instances of camera-conditioned depth features  $\mathbf{D}|\mathbf{E}$ , corresponding to different decoder resolutions, as described in Sec. III-E.

TABLE X

<span id="page-9-2"></span>Loss ablations.  $\mathcal{L}_{\mathrm{EG-SSI}}$  refers to either employing or not the proposed Edge-Guided Normalized loss;  $\mathbf{O}_{\mathcal{L}_{\mathrm{con}}}$  indicates the output there the geometry consistency loss is applied to.

|   | CEC SSI                       | Oc                           |                          | Zero-sh               |                |                        |
|---|-------------------------------|------------------------------|--------------------------|-----------------------|----------------|------------------------|
|   | $\mathcal{L}_{\text{EG-SSI}}$ | $\mathcal{L}_{\mathrm{con}}$ | $\mid \delta_1 \uparrow$ | $SI_{log} \downarrow$ | $F_A \uparrow$ | $\rho_{\rm A}\uparrow$ |
| 1 | ×                             | $\mathbf{D} \mathbf{E}$      | 54.5                     | 16.3                  | 56.0           | 77.9                   |
| 2 | ×                             | $\mathbf{Z}$                 | 55.3                     | 16.2                  | 56.1           | 78.2                   |
| 3 | ✓                             | ${\bf Z}$                    | 60.0                     | 15.3                  | 57.9           | 79.8                   |

#### TABLE XI

<span id="page-9-3"></span>MODEL ABLATIONS. THE "MODEL" COLUMN REFERS TO ARCHITECTURE AND TRAINING STRATEGY EMPLOYED. "V1" IS THE ORIGINAL UNIDEPTH, WHILE "V2" IS THE PROPOSED UNIDEPTHV2. "COND" SPECIFIES WHETHER THE CAMERA-PROMPTING MECHANISM IS PRESENT OR NOT.

|   | Model | Cond |                     | Zero-sh               | ot Test        |                        |
|---|-------|------|---------------------|-----------------------|----------------|------------------------|
|   | Model | Cond | $\delta_1 \uparrow$ | $SI_{log} \downarrow$ | $F_A \uparrow$ | $\rho_{\rm A}\uparrow$ |
| 1 | V1    | Х    | 50.1                | 18.0                  | 50.8           | 76.7                   |
| 2 | V1    | ✓    | 54.5                | 16.4                  | 56.1           | 77.1                   |
| 3 | V2    | X    | 49.3                | 18.4                  | 49.2           | 76.6                   |
| 4 | V2    | ✓    | 54.5                | 16.3                  | 56.0           | 77.9                   |

This contrasts with the original UniDepth [17], which relied on a single conditioning point. Given this architectural shift, we argue that deep conditioning may not be optimal. Features at different resolutions encode varying levels of abstraction, and enforcing deep conditioning introduces additional design freedom. Table X investigates where to apply the consistency loss ( $\mathcal{L}_{con}$ ) from [17]: either directly in the output space ( $\mathbf{Z}$ , row 2) or within the camera-conditioned features at each scale ( $\mathbf{D}|\mathbf{E}$ , row 1). The results indicate minimal differences from applying the loss directly in the output space. Therefore, based on Occam's razor, we adopt the simpler and more effective design from row 2 as the final approach.

**Conditioning Impact.** As previously explored in [17], we analyze the impact of our proposed camera conditioning in Table XI. This ablation includes both UniDepth and UniDepthV2 under the same conditions—without  $\mathcal{L}_{\mathrm{EG-SSI}}$  and without invariance applied to deep features ( $\mathbf{D}|\mathbf{E}$ ). The results show that conditioning has an even stronger positive effect for UniDepthV2, as evidenced by comparing row 3 vs. row 4 against the comparison of row 1 vs. row 2.

<span id="page-10-4"></span>![](_page_10_Picture_1.jpeg)

Fig. 7. Failure and Edge Cases. UniDepthV2 is run on challenging images collected from the internet. The domains include mirrors, non-pinhole cameras, paintings, and optical illusions, both from cameras and drawings.

#### TABLE XII

<span id="page-10-3"></span><span id="page-10-2"></span>REPRESENTATION. THE "REPR" COLUMN REFERS TO DIRECT CARTESIAN REGRESSION (*xyz*) REGRESSION *vs*. UNIDEPTH'S PSEUDO-SPHERICAL OUTPUT (*sph*). THE "MODEL" COLUMN REFERS TO ARCHITECTURE AND TRAINING STRATEGY EMPLOYED: "V1" IS THE ORIGINAL UNIDEPTH, WHILE "V2" IS THE PROPOSED UNIDEPTHV2.

|   |       |      |         | Zero-shot Test |         |         |
|---|-------|------|---------|----------------|---------|---------|
|   | Model | Repr | δ1<br>↑ | SIlog<br>↓     | FA<br>↑ | ρA<br>↑ |
| 1 | V1    | xyz  | 48.2    | 21.2           | 41.2    | 61.3    |
| 2 | V1    | sph  | 54.5    | 16.4           | 56.1    | 77.1    |
| 3 | V2    | xyz  | 49.1    | 20.4           | 38.8    | 60.2    |
| 4 | V2    | sph  | 60.0    | 15.3           | 57.9    | 79.8    |

Camera Disentanglement. We re-evaluate the output representation for UniDepthV2 in Tab. [XII,](#page-10-2) mirroring the analysis in [\[17\]](#page-11-8). With otherwise matched camera settings, we observe a similar comparative picture in the UniDepthV2 setting: a significant benefit of our pseudo-spherical representation for depth-specific metrics and a substantial benefit for 3D and camera accuracy.

Confidence. We evaluate in Tab. [VII](#page-8-4) the confidence estimator introduced in Sec. [III-E](#page-4-0) on the validation splits of the training datasets ("In-domain") and on unseen datasets ("Zero-shot"). In-domain, uncertainty aligns well with error: nAUSE is low (0.199–0.221) and ρ is high (0.68–0.74), both improving as model capacity is increased. Under domain shift, the quality drops, *i*.*e*. nAUSE rises to 0.54–0.65 and ρ falls to 0.29, *i*.*e*. indicating that ranking is partly preserved but calibration degrades. The opposing trend, namely slightly higher ρ yet worse nAUSE for larger models, is probably capacity-driven overfitting: bigger models learn sharper, edge-focused uncertainty priors that order local errors correctly while misestimating their magnitude in novel domains. Nevertheless, even zero-shot uncertainty remains informative and far from random, enabling reliability-aware masking and exploiting our resolution/speed trade-offs at inference.

## *D. Failure Cases and Limitations*

We present in Fig. [7](#page-10-3) six images from the internet that pose unusual, challenging conditions for depth models, including mirrors, paintings, optical illusions, and non-pinhole projection. While UniDepthV2 does not exhibit catastrophic failures on these examples, it can resolve certain human-related optical illusions and correctly recognize a painting when its frame and contextual objects are visible (*e*.*g*. "Liberty Leading the People"). However, it struggles with non-realistic paintings and distorted geometry (*e*.*g*. "Starry Night"), though it still separates foreground from background. Mirrors remain particularly challenging and ambiguous: without sufficient context, the model often interprets them as just a cavity and accommodates strong deformation. In addition, UniDepthV2 struggles to represent non-pinhole projection and is not able to rectify the deformation as the implicit camera representation is pinholebased as described in Sec. [III-B.](#page-3-0)

## V. CONCLUSION

We introduced UniDepthV2, a universal monocular metric depth estimation model that enhances generalization across diverse domains without requiring camera parameters at test time. By improving both the model architecture and introducing new loss functions in the training objective, UniDepthV2 achieves state-of-the-art performance while enhancing computational efficiency, as demonstrated through extensive zero-shot and fine-tuning evaluations. Additionally, our training strategy enables a flexible trade-off between inference speed and detail preservation by allowing variable input resolutions at test time while maintaining global scale consistency.

## ACKNOWLEDGMENTS

This work is funded by Toyota Motor Europe via the research project TRACE-Zurich. Additional thanks to Lavinia Recchioni ¨ for her editing and unwavering support.

#