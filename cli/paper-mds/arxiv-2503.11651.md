# VGGT: Visual Geometry Grounded Transformer

<span id="page-0-0"></span>Jianyuan Wang<sup>1</sup>,<sup>2</sup> Minghao Chen<sup>1</sup>,<sup>2</sup> Nikita Karaev<sup>1</sup>,<sup>2</sup> Andrea Vedaldi<sup>1</sup>,<sup>2</sup>

Christian Rupprecht<sup>1</sup> David Novotny<sup>2</sup>

<sup>1</sup>Visual Geometry Group, University of Oxford <sup>2</sup>Meta AI

![](_page_0_Picture_5.jpeg)

Figure 1. VGGT is a large feed-forward transformer with minimal 3D-inductive biases trained on a trove of 3D-annotated data. It accepts up to hundreds of images and predicts cameras, point maps, depth maps, and point tracks for all images at once in less than a second, which often outperforms optimization-based alternatives without further processing.

## Abstract

*We present VGGT, a feed-forward neural network that directly infers all key 3D attributes of a scene, including camera parameters, point maps, depth maps, and 3D point tracks, from one, a few, or hundreds of its views. This approach is a step forward in 3D computer vision, where models have typically been constrained to and specialized for single tasks. It is also simple and efficient, reconstructing images in under one second, and still outperforming alternatives that require post-processing with visual geometry optimization techniques. The network achieves state-of-the-art results in multiple 3D tasks, including camera parameter estimation, multi-view depth estimation, dense point cloud reconstruction, and 3D point tracking. We also show that using pretrained VGGT as a feature backbone significantly enhances downstream tasks, such as non-rigid point tracking and feed-forward novel view synthesis. Code and models are publicly available at [https://github.com/facebookresearch/vggt.](https://github.com/facebookresearch/vggt)*

## 1. Introduction

We consider the problem of estimating the 3D attributes of a scene, captured in a set of images, utilizing a feedforward neural network. Traditionally, 3D reconstruction has been approached with visual-geometry methods, utilizing iterative optimization techniques like Bundle Adjustment (BA) [\[45\]](#page-14-0). Machine learning has often played an important complementary role, addressing tasks that cannot be solved by geometry alone, such as feature matching and monocular depth prediction. The integration has become increasingly tight, and now state-of-the-art Structure-from-Motion (SfM) methods like VGGSfM [\[125\]](#page-17-0) combine machine learning and visual geometry end-to-end via differentiable BA. Even so, visual geometry *still* plays a major role in 3D reconstruction, which increases complexity and computational cost.

As networks become ever more powerful, we ask if, finally, 3D tasks can be solved *directly* by a neural network, eschewing geometry post-processing almost entirely. Recent contributions like DUSt3R [\[129\]](#page-17-1) and its evolution <span id="page-1-0"></span>MASt3R [\[62\]](#page-15-0) have shown promising results in this direction, but these networks can only process two images at once and rely on post-processing to reconstruct more images, fusing pairwise reconstructions.

In this paper, we take a further step towards removing the need to optimize 3D geometry in post-processing. We do so by introducing *Visual Geometry Grounded Transformer* (VGGT), a feed-forward neural network that performs 3D reconstruction from one, a few, or even hundreds of input views of a scene. VGGT predicts a full set of 3D attributes, including camera parameters, depth maps, point maps, and 3D point tracks. It does so in a single forward pass, in seconds. Remarkably, it often outperforms optimization-based alternatives even without further processing. This is a substantial departure from DUSt3R, MASt3R, or VGGSfM, which still require costly iterative post-optimization to obtain usable results.

We also show that it is unnecessary to design a special network for 3D reconstruction. Instead, VGGT is based on a fairly standard large transformer [\[119\]](#page-17-2), with no particular 3D or other inductive biases (except for alternating between frame-wise and global attention), but trained on a large number of publicly available datasets with 3D annotations. VGGT is thus built in the same mold as large models for natural language processing and computer vision, such as GPTs [\[1,](#page-12-0) [29,](#page-13-0) [148\]](#page-18-0), CLIP [\[86\]](#page-16-0), DINO [\[10,](#page-12-1) [78\]](#page-15-1), and Stable Diffusion [\[34\]](#page-14-1). These have emerged as versatile backbones that can be fine-tuned to solve new, specific tasks. Similarly, we show that the features computed by VGGT can significantly enhance downstream tasks like point tracking in dynamic videos, and novel view synthesis.

There are several recent examples of large 3D neural networks, including DepthAnything [\[142\]](#page-18-1), MoGe [\[128\]](#page-17-3), and LRM [\[49\]](#page-14-2). However, these models only focus on a single 3D task, such as monocular depth estimation or novel view synthesis. In contrast, VGGT uses a shared backbone to predict all 3D quantities of interest together. We demonstrate that *learning* to predict these interrelated 3D attributes enhances overall accuracy despite potential redundancies. At the same time, we show that, during *inference*, we can derive the point maps from separately predicted depth and camera parameters, obtaining better accuracy compared to directly using the dedicated point map head.

To summarize, we make the following contributions: (1) We introduce VGGT, a large feed-forward transformer that, given one, a few, or even hundreds of images of a scene, can predict all its key 3D attributes, including camera intrinsics and extrinsics, point maps, depth maps, and 3D point tracks, in seconds. (2) We demonstrate that VGGT's predictions are directly usable, being highly competitive and usually better than those of state-of-the-art methods that use slow post-processing optimization techniques. (3) We also show that, when further combined with BA post-processing, VGGT achieves state-of-the-art results across the board, even when compared to methods that specialize in a subset of 3D tasks, often improving quality substantially.

We make our code and models publicly available at [https://github.com/facebookresearch/vggt.](https://github.com/facebookresearch/vggt) We believe that this will facilitate further research in this direction and benefit the computer vision community by providing a new foundation for fast, reliable, and versatile 3D reconstruction.

## 2. Related Work

Structure from Motion is a classic computer vision problem [\[45,](#page-14-0) [77,](#page-15-2) [80\]](#page-15-3) that involves estimating camera parameters and reconstructing sparse point clouds from a set of images of a static scene captured from different viewpoints. The traditional SfM pipeline [\[2,](#page-12-2) [36,](#page-14-3) [70,](#page-15-4) [94,](#page-16-1) [103,](#page-16-2) [134\]](#page-18-2) consists of multiple stages, including image matching, triangulation, and bundle adjustment. COLMAP [\[94\]](#page-16-1) is the most popular framework based on the traditional pipeline. In recent years, deep learning has improved many components of the SfM pipeline, with keypoint detection [\[21,](#page-13-1) [31,](#page-14-4) [116,](#page-17-4) [149\]](#page-18-3) and image matching [\[11,](#page-13-2) [67,](#page-15-5) [92,](#page-16-3) [99\]](#page-16-4) being two primary areas of focus. Recent methods [\[5,](#page-12-3) [102,](#page-16-5) [109,](#page-17-5) [112,](#page-17-6) [113,](#page-17-7) [118,](#page-17-8) [122,](#page-17-9) [125,](#page-17-0) [131,](#page-17-10) [160\]](#page-19-0) explored end-to-end differentiable SfM, where VGGSfM [\[125\]](#page-17-0) started to outperform traditional algorithms on challenging phototourism scenarios.

Multi-view Stereo aims to densely reconstruct the geometry of a scene from multiple overlapping images, typically assuming known camera parameters, which are often estimated with SfM. MVS methods can be divided into three categories: traditional handcrafted [\[38,](#page-14-5) [39,](#page-14-6) [96,](#page-16-6) [130\]](#page-17-11), global optimization [\[37,](#page-14-7) [74,](#page-15-6) [133,](#page-18-4) [147\]](#page-18-5), and learning-based methods [\[42,](#page-14-8) [72,](#page-15-7) [84,](#page-16-7) [145,](#page-18-6) [157\]](#page-18-7). As in SfM, learning-based MVS approaches have recently seen a lot of progress. Here, DUSt3R [\[129\]](#page-17-1) and MASt3R [\[62\]](#page-15-0) directly estimate aligned dense point clouds from a pair of views, similar to MVS but without requiring camera parameters. Some concurrent works [\[111,](#page-17-12) [127,](#page-17-13) [141,](#page-18-8) [156\]](#page-18-9) explore replacing DUSt3R's test-time optimization with neural networks, though these attempts achieve only suboptimal or comparable performance to DUSt3R. Instead, VGGT outperforms DUSt3R and MASt3R by a large margin.

Tracking-Any-Point was first introduced in Particle Video [\[91\]](#page-16-8) and revived by PIPs [\[44\]](#page-14-9) during the deep learning era, aiming to track points of interest across video sequences including dynamic motions. Given a video and some 2D query points, the task is to predict 2D correspondences of these points in all other frames. TAP-Vid [\[23\]](#page-13-3) proposed three benchmarks for this task and a simple baseline method later improved in TAPIR [\[24\]](#page-13-4). CoTracker [\[55,](#page-14-10) [56\]](#page-14-11) utilized correlations between different points to track through occlusions, while DOT [\[60\]](#page-15-8) enabled dense tracking through occlusions. Recently, TAPTR [\[63\]](#page-15-9) proposed

<span id="page-2-1"></span>![](_page_2_Figure_0.jpeg)

Figure 2. **Architecture Overview.** Our model first patchifies the input images into tokens by DINO, and appends camera tokens for camera prediction. It then alternates between frame-wise and global self attention layers. A camera head makes the final prediction for camera extrinsics and intrinsics, and a DPT [87] head for any dense output.

an end-to-end transformer for this task, and LocoTrack [13] extended commonly used pointwise features to nearby regions. All of these methods are specialized point trackers. Here, we demonstrate that VGGT's features yield state-of-the-art tracking performance when coupled with existing point trackers.

### 3. Method

We introduce VGGT, a large transformer that ingests a set of images as input and produces a variety of 3D quantities as output. We start by introducing the problem in Sec. 3.1, followed by our architecture in Sec. 3.2 and its prediction heads in Sec. 3.3, and finally the training setup in Sec. 3.4.

#### <span id="page-2-0"></span>3.1. Problem definition and notation

The input is a sequence  $(I_i)_{i=1}^N$  of N RGB images  $I_i \in \mathbb{R}^{3 \times H \times W}$ , observing the same 3D scene. VGGT's transformer is a function that maps this sequence to a corresponding set of 3D annotations, one per frame:

$$f((I_i)_{i=1}^N) = (\mathbf{g}_i, D_i, P_i, T_i)_{i=1}^N.$$
 (1)

The transformer thus maps each image  $I_i$  to its camera parameters  $\mathbf{g}_i \in \mathbb{R}^9$  (intrinsics and extrinsics), its depth map  $D_i \in \mathbb{R}^{H \times W}$ , its point map  $P_i \in \mathbb{R}^{3 \times H \times W}$ , and a grid  $T_i \in \mathbb{R}^{C \times H \times W}$  of C-dimensional features for point tracking. We explain next how these are defined.

For the **camera parameters**  $\mathbf{g}_i$ , we use the parametrization from [125] and set  $\mathbf{g} = [\mathbf{q}, \mathbf{t}, \mathbf{f}]$  which is the concatenation of the rotation quaternion  $\mathbf{q} \in \mathbb{R}^4$ , the translation vector  $\mathbf{t} \in \mathbb{R}^3$ , and the field of view  $\mathbf{f} \in \mathbb{R}^2$ . We assume that the camera's principal point is at the image center, which is common in SfM frameworks [95, 125].

We denote the domain of the image  $I_i$  with  $\mathcal{I}(I_i) = \{1,\ldots,H\} \times \{1,\ldots,W\}$ , *i.e.*, the set of pixel locations. The **depth map**  $D_i$  associates each pixel location  $\mathbf{y} \in \mathcal{I}(I_i)$  with its corresponding depth value  $D_i(\mathbf{y}) \in \mathbb{R}^+$ , as observed from the i-th camera. Likewise, the **point map**  $P_i$  associates each pixel with its corresponding 3D scene point  $P_i(\mathbf{y}) \in \mathbb{R}^3$ . Importantly, like in DUSt3R [129], the point maps are *viewpoint invariant*, meaning that the 3D points  $P_i(\mathbf{y})$  are defined in the coordinate system of the first camera  $\mathbf{g}_1$ , which we take as the world reference frame.

Finally, for **keypoint tracking**, we follow track-any-point methods such as [25, 57]. Namely, given a fixed query image point  $\mathbf{y}_q$  in the query image  $I_q$ , the network outputs a track  $\mathcal{T}^*(\mathbf{y}_q) = (\mathbf{y}_i)_{i=1}^N$  formed by the corresponding 2D points  $\mathbf{y}_i \in \mathbb{R}^2$  in all images  $I_i$ .

Note that the transformer f above does not output the tracks directly but instead features  $T_i \in \mathbb{R}^{C \times H \times W}$ , which are used for tracking. The tracking is delegated to a separate module, described in Sec. 3.3, which implements a function  $\mathcal{T}((\mathbf{y}_j)_{j=1}^M, (T_i)_{i=1}^N) = ((\hat{\mathbf{y}}_{j,i})_{i=1}^N)_{j=1}^M$ . It ingests the query point  $\mathbf{y}_q$  and the dense tracking features  $T_i$  output by the transformer f and then computes the track. The two networks f and  $\mathcal{T}$  are trained jointly end-to-end.

**Order of Predictions.** The order of the images in the input sequence is arbitrary, except that the first image is chosen as the reference frame. The network architecture is designed to be permutation equivariant for all but the first frame.

**Over-complete Predictions.** Notably, not all quantities predicted by VGGT are independent. For example, as shown by DUSt3R [129], the camera parameters g can be inferred from the invariant point map P, for instance, by solving the Perspective-n-Point (PnP) problem [35, 61].

<span id="page-3-4"></span><span id="page-3-3"></span>![](_page_3_Figure_0.jpeg)

Figure 3. Qualitative comparison of our predicted 3D points to DUSt3R on in-the-wild images. As shown in the top row, our method successfully predicts the geometric structure of an oil painting, while DUSt3R predicts a slightly distorted plane. In the second row, our method correctly recovers a 3D scene from two images with no overlap, while DUSt3R fails. The third row provides a challenging example with repeated textures, while our prediction is still high-quality. We do not include examples with more than 32 frames, as DUSt3R runs out of memory beyond this limit.

Furthermore, the depth maps can be deduced from the point map and the camera parameters. However, as we show in Sec. 4.5, tasking VGGT with explicitly predicting *all* aforementioned quantities during training brings substantial performance gains, even when these are related by closed-form relationships. Meanwhile, during inference, it is observed that combining independently estimated depth maps and camera parameters produces more accurate 3D points compared to directly employing a specialized point map branch.

### <span id="page-3-0"></span>3.2. Feature Backbone

Following recent works in 3D deep learning [53, 129, 132], we design a simple architecture with minimal 3D inductive biases, letting the model learn from ample quantities of 3D-annotated data. In particular, we implement the model f as a large transformer [119]. To this end, each input image I is initially patchified into a set of K tokens  $t^I \in \mathbb{R}^{K \times C}$  through DINO [78]. The combined set of image tokens from all frames, i.e.,  $t^I = \bigcup_{i=1}^N \{t_i^I\}$ , is subsequently processed through the main network structure, alternating frame-wise and global self-attention layers.

Alternating-Attention. We slightly adjust the standard transformer design by introducing Alternating-Attention

(AA), making the transformer focus within each frame and globally in an alternate fashion. Specifically, frame-wise self-attention attends to the tokens  $\mathbf{t}_k^I$  within each frame separately, and global self-attention attends to the tokens  $\mathbf{t}^I$  across all frames jointly. This strikes a balance between integrating information across different images and normalizing the activations for the tokens within each image. By default, we employ L=24 layers of global and frame-wise attention. In Sec. 4, we demonstrate that our AA architecture brings significant performance gains. Note that our architecture does not employ any cross-attention layers, only self-attention ones.

#### <span id="page-3-1"></span>3.3. Prediction heads

Here, we describe how f predicts the camera parameters, depth maps, point maps, and point tracks. First, for each input image  $I_i$ , we augment the corresponding image tokens  $\mathbf{t}_i^I$  with an additional camera token  $\mathbf{t}_i^\mathbf{g} \in \mathbb{R}^{1 \times C'}$  and four register tokens [19]  $\mathbf{t}_i^R \in \mathbb{R}^{4 \times C'}$ . The concatenation of  $(\mathbf{t}_i^I, \mathbf{t}_i^\mathbf{g}, \mathbf{t}_i^Rj)_{i=1}^N$  is then passed to the AA transformer, yielding output tokens  $(\hat{\mathbf{t}}_i^I, \hat{\mathbf{t}}_i^\mathbf{g}, \hat{\mathbf{t}}_i^R)_{i=1}^N$ . Here, the camera token and register tokens of the first frame  $(\mathbf{t}_1^\mathbf{g} := \bar{\mathbf{t}}^\mathbf{g}, \mathbf{t}_1^R := \bar{\mathbf{t}}^R)$  are set to a different set of learnable tokens  $\bar{\mathbf{t}}^\mathbf{g}, \bar{\mathbf{t}}^R$  than those of all other frames  $(\mathbf{t}_i^\mathbf{g} := \bar{\bar{\mathbf{t}}}^\mathbf{g}, \mathbf{t}_i^R := \bar{\bar{\mathbf{t}}}^R, i \in [2, \dots, N])$ ,

<span id="page-3-2"></span><sup>&</sup>lt;sup>1</sup>The number of tokens depends on the image resolution.

<span id="page-4-1"></span><span id="page-4-0"></span>![](_page_4_Picture_0.jpeg)

Figure 4. Additional Visualizations of Point Map Estimation. Camera frustums illustrate the estimated camera poses. Explore our interactive demo for better visualization quality.

which are also learnable. This allows the model to distinguish the first frame from the rest, and to represent the 3D predictions in the coordinate frame of the first camera. Note that the refined camera and register tokens now become frame-specific—this is because our AA transformer contains frame-wise self-attention layers that allow the transformer to match the camera and register tokens with the corresponding tokens from the same image. Following common practice, the output register tokens  $\hat{\bf t}_i^R$  are discarded while  $\hat{\bf t}_i^I$ ,  $\hat{\bf t}_i^g$  are used for prediction.

**Coordinate Frame.** As noted above, we predict cameras, point maps, and depth maps in the coordinate frame of the first camera  $\mathbf{g}_1$ . As such, the camera extrinsics output for the first camera are set to the identity, *i.e.*, the first rotation quaternion is  $\mathbf{q}_1 = [0,0,0,1]$  and the first translation vector is  $\mathbf{t}_1 = [0,0,0]$ . Recall that the special camera and register tokens  $\mathbf{t}_1^{\mathbf{g}} := \overline{\mathbf{t}}^{\mathbf{g}}, \mathbf{t}_1^R := \overline{\mathbf{t}}^R$  allow the transformer to identify the first camera.

**Camera Predictions.** The camera parameters  $(\hat{\mathbf{g}}^i)_{i=1}^N$  are predicted from the output camera tokens  $(\hat{\mathbf{t}}_i^{\mathbf{g}})_{i=1}^N$  using four additional self-attention layers followed by a linear layer. This forms the *camera head* that predicts the camera intrin-

sics and extrinsics.

**Dense Predictions.** The output image tokens  $\hat{\mathbf{t}}_i^I$  are used to predict the dense outputs, *i.e.*, the depth maps  $D_i$ , point maps  $P_i$ , and tracking features  $T_i$ . More specifically,  $\hat{\mathbf{t}}_i^I$  are first converted to dense feature maps  $F_i \in \mathbb{R}^{C'' \times H \times W}$  with a DPT layer [87]. Each  $F_i$  is then mapped with a  $3 \times 3$  convolutional layer to the corresponding depth and point maps  $D_i$  and  $P_i$ . Additionally, the DPT head also outputs dense features  $T_i \in \mathbb{R}^{C \times H \times W}$ , which serve as input to the tracking head. We also predict the aleatoric uncertainty [58, 76]  $\Sigma_i^D \in \mathbb{R}_+^{H \times W}$  and  $\Sigma_i^P \in \mathbb{R}_+^{H \times W}$  for each depth and point map, respectively. As described in Sec. 3.4, the uncertainty maps are used in the loss and, after training, are proportional to the model's confidence in the predictions.

**Tracking.** In order to implement the tracking module  $\mathcal{T}$ , we use the CoTracker2 architecture [57], which takes the dense tracking features  $T_i$  as input. More specifically, given a query point  $\mathbf{y}_j$  in a query image  $I_q$  (during training, we always set q=1, but any other image can be potentially used as a query), the tracking head  $\mathcal{T}$  predicts the set of 2D points  $\mathcal{T}((\mathbf{y}_j)_{j=1}^M, (T_i)_{i=1}^N) = ((\hat{\mathbf{y}}_{j,i})_{i=1}^N)_{j=1}^M$  in all images  $I_i$  that correspond to the same 3D point as  $\mathbf{y}$ . To do so, the feature map  $T_q$  of the query image is first bilinearly sampled at

<span id="page-5-3"></span>the query point  $\mathbf{y}_j$  to obtain its feature. This feature is then correlated with all other feature maps  $T_i, i \neq q$  to obtain a set of correlation maps. These maps are then processed by self-attention layers to predict the final 2D points  $\hat{\mathbf{y}}_i$ , which are all in correspondence with  $\mathbf{y}_j$ . Note that, similar to VG-GSfM [125], our tracker does not assume any temporal ordering of the input frames and, hence, can be applied to any set of input images, not just videos.

#### <span id="page-5-0"></span>3.4. Training

**Training Losses.** We train the VGGT model f end-to-end using a multi-task loss:

<span id="page-5-2"></span>
$$\mathcal{L} = \mathcal{L}_{camera} + \mathcal{L}_{depth} + \mathcal{L}_{pmap} + \lambda \mathcal{L}_{track}. \tag{2}$$

We found that the camera ( $\mathcal{L}_{camera}$ ), depth ( $\mathcal{L}_{depth}$ ), and point-map ( $\mathcal{L}_{pmap}$ ) losses have similar ranges and do not need to be weighted against each other. The tracking loss  $\mathcal{L}_{track}$  is down-weighted with a factor of  $\lambda=0.05$ . We describe each loss term in turn.

The camera loss  $\mathcal{L}_{\text{camera}}$  supervises the cameras  $\hat{\mathbf{g}}$ :  $\mathcal{L}_{\text{camera}} = \sum_{i=1}^{N} \|\hat{\mathbf{g}}_i - \mathbf{g}_i\|_{\epsilon}$ , comparing the predicted cameras  $\hat{\mathbf{g}}_i$  with the ground truth  $\mathbf{g}_i$  using the Huber loss  $|\cdot|_{\epsilon}$ .

The depth loss  $\mathcal{L}_{\text{depth}}$  follows DUSt3R [129] and implements the aleatoric-uncertainty loss [59, 75] weighing the discrepancy between the predicted depth  $\hat{D}_i$  and the ground-truth depth  $D_i$  with the predicted uncertainty map  $\hat{\Sigma}_i^D$ . Differently from DUSt3R, we also apply a gradient-based term, which is widely used in monocular depth estimation. Hence, the depth loss is  $\mathcal{L}_{\text{depth}} = \sum_{i=1}^N \|\Sigma_i^D\odot(\hat{D}_i - \nabla D_i)\| - \alpha \log \Sigma_i^D$ , where  $\odot$  is the channel-broadcast element-wise product. The point map loss is defined analogously but with the point-map uncertainty  $\Sigma_i^P \colon \mathcal{L}_{\text{pmap}} = \sum_{i=1}^N \|\Sigma_i^P\odot(\hat{P}_i - P_i)\| + \|\Sigma_i^P\odot(\nabla \hat{P}_i - \nabla P_i)\| - \alpha \log \Sigma_i^P$ .

Finally, the tracking loss is given by  $\mathcal{L}_{\text{track}} = \sum_{j=1}^{M} \sum_{i=1}^{N} \|\mathbf{y}_{j,i} - \hat{\mathbf{y}}_{j,i}\|$ . Here, the outer sum runs over all ground-truth query points  $\mathbf{y}_{j}$  in the query image  $I_{q}$ ,  $\mathbf{y}_{j,i}$  is  $\mathbf{y}_{j}$ 's ground-truth correspondence in image  $I_{i}$ , and  $\hat{\mathbf{y}}_{j,i}$  is the corresponding prediction obtained by the application  $\mathcal{T}((\mathbf{y}_{j})_{j=1}^{M}, (T_{i})_{i=1}^{N})$  of the tracking module. Additionally, following CoTracker2 [57], we apply a visibility loss (binary cross-entropy) to estimate whether a point is visible in a given frame.

Ground Truth Coordinate Normalization. If we scale a scene or change its global reference frame, the images of the scene are not affected at all, meaning that any such variant is a legitimate result of 3D reconstruction. We remove this ambiguity by normalizing the data, thus making a canonical choice and task the transformer to output this particular variant. We follow [129] and, first, express all quantities in the coordinate frame of the first camera  $g_1$ . Then, we compute the average Euclidean distance of all 3D points in the

point map P to the origin and use this scale to normalize the camera translations  $\mathbf{t}$ , the point map P, and the depth map D. Importantly, unlike [129], we do *not* apply such normalization to the predictions output by the transformer; instead, we force it to learn the normalization we choose from the training data.

**Implementation Details.** By default, we employ L=24layers of global and frame-wise attention, respectively. The model consists of approximately 1.2 billion parameters in total. We train the model by optimizing the training loss (2) with the AdamW optimizer for 160K iterations. We use a cosine learning rate scheduler with a peak learning rate of 0.0002 and a warmup of 8K iterations. For every batch, we randomly sample 2-24 frames from a random training scene. The input frames, depth maps, and point maps are resized to a maximum dimension of 518 pixels. The aspect ratio is randomized between 0.33 and 1.0. We also randomly apply color jittering, Gaussian blur, and grayscale augmentation to the frames. The training runs on 64 A100 GPUs over nine days. We employ gradient norm clipping with a threshold of 1.0 to ensure training stability. We leverage bfloat16 precision and gradient checkpointing to improve GPU memory and computational efficiency.

Training Data. The model was trained using a large and diverse collection of datasets, including: Co3Dv2 [88], BlendMVS [146], DL3DV [69], MegaDepth [64], Kubric [41], WildRGB [135], ScanNet [18], Hyper-Sim [89], Mapillary [71], Habitat [107], Replica [104], MVS-Synth [50], PointOdyssey [159], Virtual KITTI [7], Aria Synthetic Environments [82], Aria Digital Twin [82], and a synthetic dataset of artist-created assets similar to Objaverse [20]. These datasets span various domains, including indoor and outdoor environments, and encompass synthetic and real-world scenarios. The 3D annotations for these datasets are derived from multiple sources, such as direct sensor capture, synthetic engines, or SfM techniques [95]. The combination of our datasets is broadly comparable to those of MASt3R [30] in size and diversity.

### <span id="page-5-1"></span>4. Experiments

This section compares our method to state-of-the-art approaches across multiple tasks to show its effectiveness.

#### 4.1. Camera Pose Estimation

We first evaluate our method on the CO3Dv2 [88] and RealEstate10K [161] datasets for camera pose estimation, as shown in Tab. 1. Following [124], we randomly select 10 images per scene and evaluate them using the standard metric AUC@30, which combines RRA and RTA. RRA (Relative Rotation Accuracy) and RTA (Relative Translation Accuracy) calculate the relative angular errors in rotation and translation, respectively, for each image pair. These angu-

<span id="page-6-4"></span><span id="page-6-0"></span>

| Methods                   | Re10K (unseen)<br>AUC@30↑ | CO3Dv2<br>AUC@30↑ | Time        |
|---------------------------|---------------------------|-------------------|-------------|
| Colmap+SPSG [92]          | 45.2                      | 25.3              | ~ 15s       |
| PixSfM [66]               | 49.4                      | 30.1              | > 20s       |
| PoseDiff [124]            | 48.0                      | 66.5              | $\sim 7s$   |
| DUSt3R [129]              | 67.7                      | 76.7              | $\sim 7s$   |
| MASt3R [62]               | 76.4                      | 81.8              | $\sim 9s$   |
| VGGSfM v2 [125]           | 78.9                      | 83.4              | $\sim 10s$  |
| MV-DUSt3R [111] ‡         | 71.3                      | 69.5              | ~ 0.6s      |
| CUT3R [127] <sup>‡</sup>  | 75.3                      | 82.8              | ~ 0.6s      |
| FLARE [156] <sup>‡</sup>  | 78.8                      | 83.3              | $\sim 0.5s$ |
| Fast3R [141] <sup>‡</sup> | 72.7                      | 82.5              | $\sim$ 0.2s |
| Ours (Feed-Forward)       | <u>85.3</u>               | 88.2              | $\sim$ 0.2s |
| Ours (with BA)            | 93.5                      | 91.8              | ∼ 1.8s      |

Table 1. Camera Pose Estimation on RealEstate10K [161] and CO3Dv2 [88] with 10 random frames. All metrics the higher the better. None of the methods were trained on the Re10K dataset. Runtime were measured using one H100 GPU. Methods marked with  $^\ddagger$  represent concurrent work.

<span id="page-6-1"></span>

| Known GT camera | Method              | Acc.↓ | Comp.↓ | Overall↓ |
|-----------------|---------------------|-------|--------|----------|
| 1               | Gipuma [40]         | 0.283 | 0.873  | 0.578    |
| ✓               | MVSNet [144]        | 0.396 | 0.527  | 0.462    |
| ✓               | CIDER [139]         | 0.417 | 0.437  | 0.427    |
| ✓               | PatchmatchNet [121] | 0.427 | 0.377  | 0.417    |
| ✓               | MASt3R [62]         | 0.403 | 0.344  | 0.374    |
| 1               | GeoMVSNet [157]     | 0.331 | 0.259  | 0.295    |
| x               | DUSt3R [129]        | 2.677 | 0.805  | 1.741    |
| ×               | Ours                | 0.389 | 0.374  | 0.382    |

Table 2. **Dense MVS Estimation on the DTU [51] Dataset.** Methods operating with known ground-truth camera are in the top part of the table, while the bottom part contains the methods that do not know the ground-truth camera.

<span id="page-6-2"></span>

| Methods            | Acc.↓ | Comp.↓ | Overall↓ | Time         |
|--------------------|-------|--------|----------|--------------|
| DUSt3R             | 1.167 | 0.842  | 1.005    | $\sim 7s$    |
| MASt3R             | 0.968 | 0.684  | 0.826    | $\sim 9s$    |
| Ours (Point)       | 0.901 | 0.518  | 0.709    | $\sim 0.2s$  |
| Ours (Depth + Cam) | 0.873 | 0.482  | 0.677    | $\sim 0.2 s$ |

Table 3. **Point Map Estimation on ETH3D [97].** DUSt3R and MASt3R use global alignment while ours is feed-forward and, hence, much faster. The row *Ours (Point)* indicates the results using the point map head directly, while *Ours (Depth + Cam)* denotes constructing point clouds from the depth map head combined with the camera head.

lar errors are then thresholded to determine the accuracy scores. AUC is the area under the accuracy-threshold curve of the minimum values between RRA and RTA across varying thresholds. The (learnable) methods in Tab. 1 have been trained on Co3Dv2 and **not** on RealEstate10K. Our feedforward model consistently outperforms competing meth-

<span id="page-6-3"></span>

| Method         | AUC@5↑ | AUC@10↑ | AUC@20↑ |
|----------------|--------|---------|---------|
| SuperGlue [92] | 16.2   | 33.8    | 51.8    |
| LoFTR [105]    | 22.1   | 40.8    | 57.6    |
| DKM [32]       | 29.4   | 50.7    | 68.3    |
| CasMTR [9]     | 27.1   | 47.0    | 64.4    |
| Roma [33]      | 31.8   | 53.4    | 70.9    |
| Ours           | 33.9   | 55.2    | 73.4    |

Table 4. **Two-View matching comparison on ScanNet-1500** [18, 92]. Although our tracking head is not specialized for the two-view setting, it outperforms the state-of-the-art two-view matching method Roma. Measured in AUC (higher is better).

ods across all metrics on both datasets, including those that employ computationally expensive post-optimization steps, such as Global Alignment for DUSt3R/MASt3R and Bundle Adjustment for VGGSfM, typically requiring more than 10 seconds. In contrast, VGGT achieves superior performance while only operating in a feed-forward manner, requiring just 0.2 seconds on the same hardware. Compared to concurrent works [111, 127, 141, 156] (indicated by ‡), our method demonstrates significant performance advantages, with speed similar to the fastest variant Fast3R [141]. Furthermore, our model's performance advantage is even more pronounced on the RealEstate10K dataset, which none of the methods presented in Tab. 1 were trained on. This validates the superior generalization of VGGT.

Our results also show that VGGT can be improved even further by combining it with optimization methods from visual geometry optimization like BA. Specifically, refining the predicted camera poses and tracks with BA further improves accuracy. Note that our method directly predicts close-to-accurate point/depth maps, which can serve as a good initialization for BA. This eliminates the need for triangulation and iterative refinement in BA as done by [125], making our approach significantly faster (only around 2 seconds even with BA). Hence, while the feed-forward mode of VGGT outperforms all previous alternatives (whether they are feed-forward or not), there is still room for improvement since post-optimization still brings benefits.

### 4.2. Multi-view Depth Estimation

Following MASt3R [62], we further evaluate our multiview depth estimation results on the DTU [51] dataset. We report the standard DTU metrics, including Accuracy (the smallest Euclidean distance from the prediction to ground truth), Completeness (the smallest Euclidean distance from the ground truth to prediction), and their average Overall (*i.e.*, Chamfer distance). In Tab. 2, DUSt3R and our VGGT are the only two methods operating without the knowledge of ground truth cameras. MASt3R derives depth maps by triangulating matches using the ground truth cameras. Meanwhile, deep multi-view stereo methods like GeoMVS-

<span id="page-7-2"></span>![](_page_7_Figure_0.jpeg)

Figure 5. Visualization of Rigid and Dynamic Point Tracking. Top: VGGT's tracking module T outputs keypoint tracks for an unordered set of input images depicting a static scene. Bottom: We finetune the backbone of VGGT to enhance a dynamic point tracker CoTracker [\[56\]](#page-14-11), which processes sequential inputs.

Net use ground truth cameras to construct cost volumes.

Our method substantially outperforms DUSt3R, reducing the Overall score from 1.741 to 0.382. More importantly, it achieves results comparable to methods that know ground-truth cameras at test time. The significant performance gains can likely be attributed to our model's multiimage training scheme that teaches it to reason about multiview triangulation natively, instead of relying on ad hoc alignment procedures, such as in DUSt3R, which only averages multiple pairwise camera triangulations.

## 4.3. Point Map Estimation

We also compare the accuracy of our predicted point cloud to DUSt3R and MASt3R on the ETH3D [\[97\]](#page-16-15) dataset. For each scene, we randomly sample 10 frames. The predicted point cloud is aligned to the ground truth using the Umeyama [\[117\]](#page-17-17) algorithm. The results are reported after filtering out invalid points using the official masks. We report Accuracy, Completeness, and Overall (Chamfer distance) for point map estimation. As shown in Tab. [3,](#page-6-2) although DUSt3R and MASt3R conduct expensive optimization (global alignment–—around 10 seconds per scene), our method still outperforms them significantly in a simple feed-forward regime at only 0.2 seconds per reconstruction.

Meanwhile, compared to directly using our estimated point maps, we found that the predictions from our depth and camera heads (*i.e*., unprojecting the predicted depth maps to 3D using the predicted camera parameters) yield higher accuracy. We attribute this to the benefits of decomposing a complex task (point map estimation) into simpler subproblems (depth map and camera prediction), even though camera, depth maps, and point maps are jointly supervised during training.

We present a qualitative comparison with DUSt3R on inthe-wild scenes in Fig. [3](#page-3-3) and further examples in Fig. [4.](#page-4-0) VGGT outputs high-quality predictions and generalizes

<span id="page-7-1"></span>

| ETH3D Dataset              | Acc.↓ | Comp.↓ | Overall↓ |
|----------------------------|-------|--------|----------|
| Cross-Attention            | 1.287 | 0.835  | 1.061    |
| Global Self-Attention Only | 1.032 | 0.621  | 0.827    |
| Alternating-Attention      | 0.901 | 0.518  | 0.709    |

Table 5. Ablation Study for Transformer Backbone on ETH3D. We compare our alternating-attention architecture against two variants: one using only global self-attention and another employing cross-attention.

well, excelling on challenging out-of-domain examples, such as oil paintings, non-overlapping frames, and scenes with repeating or homogeneous textures like deserts.

## 4.4. Image Matching

Two-view image matching is a widely-explored topic [\[68,](#page-15-21) [93,](#page-16-17) [105\]](#page-16-16) in computer vision. It represents a specific case of rigid point tracking, which is restricted to only two views, and hence a suitable evaluation benchmark to measure our tracking accuracy, even though our model is not specialized for this task. We follow the standard protocol [\[33,](#page-14-19) [93\]](#page-16-17) on the ScanNet dataset [\[18\]](#page-13-8) and report the results in Tab. [4.](#page-6-3) For each image pair, we extract the matches and use them to estimate an essential matrix, which is then decomposed to a relative camera pose. The final metric is the relative pose accuracy, measured by AUC. For evaluation, we use ALIKED [\[158\]](#page-18-14) to detect keypoints, treating them as query points yq. These are then passed to our tracking branch T to find correspondences in the second frame. We adopt the evaluation hyperparameters (*e.g*., the number of matches, RANSAC thresholds) from Roma [\[33\]](#page-14-19). Despite not being explicitly trained for two-view matching, Tab. [4](#page-6-3) shows that VGGT achieves the highest accuracy among all baselines.

## <span id="page-7-0"></span>4.5. Ablation Studies

Feature Backbone. We first validate the effectiveness of our proposed Alternating-Attention design by comparing it

<span id="page-8-3"></span><span id="page-8-0"></span>

| w. $\mathcal{L}_{camera}$ | w. $\mathcal{L}_{depth}$ | w. $\mathcal{L}_{track}$ | Acc.↓ | Comp.↓ | Overall↓ |
|---------------------------|--------------------------|--------------------------|-------|--------|----------|
| Х                         | /                        | /                        | 1.042 | 0.627  | 0.834    |
| /                         | X                        | /                        | 0.920 | 0.534  | 0.727    |
| /                         | /                        | X                        | 0.976 | 0.603  | 0.790    |
| ✓                         | 1                        | 1                        | 0.901 | 0.518  | 0.709    |

Table 6. Ablation Study for Multi-task Learning, which shows that simultaneous training with camera, depth and track estimation yields the highest accuracy in point map estimation on ETH3D.

against two alternative attention architectures: (a) global self-attention only, and (b) cross-attention. To ensure a fair comparison, all model variants maintain an identical number of parameters, using a total of 2L attention layers. For the cross-attention variant, each frame independently attends to tokens from all other frames, maximizing cross-frame information fusion although significantly increasing the runtime, particularly as the number of input frames grows. The hyperparameters such as the hidden dimension and the number of heads are kept the same. Point map estimation accuracy is chosen as the evaluation metric for our ablation study, as it reflects the model's joint understanding of scene geometry and camera parameters. Results in Tab. 5 demonstrate that our Alternating-Attention architecture outperforms both baseline variants by a clear margin. Additionally, our other preliminary exploratory experiments consistently showed that architectures using crossattention generally underperform compared to those exclusively employing self-attention.

**Multi-task Learning.** We also verify the benefit of training a single network to simultaneously learn multiple 3D quantities, even though these outputs may potentially overlap (*e.g.*, depth maps and camera parameters together can produce point maps). As shown in Tab. 6, there is a noticeable decrease in the accuracy of point map estimation when training without camera, depth, or track estimation. Notably, incorporating camera parameter estimation clearly enhances point map accuracy, whereas depth estimation contributes only marginal improvements.

#### 4.6. Finetuning for Downstream Tasks

We now show that the VGGT pre-trained feature extractor can be reused in downstream tasks. We show this for feedforward novel view synthesis and dynamic point tracking.

**Feed-forward Novel View Synthesis** is progressing rapidly [8, 43, 49, 53, 108, 126, 140, 155]. Most existing methods take images with known camera parameters as input and predict the target image corresponding to a new camera viewpoint. Instead of relying on an explicit 3D representation, we follow LVSM [53] and modify VGGT to *directly* output the target image. However, we *do not* assume known camera parameters for the input frames.

We follow the training and evaluation protocol of LVSM

<span id="page-8-2"></span>![](_page_8_Picture_8.jpeg)

Figure 6. Qualitative Examples of Novel View Synthesis. The top row shows the input images, the middle row displays the ground truth images from target viewpoints, and the bottom row presents our synthesized images.

<span id="page-8-1"></span>

| Method       | Known Input Cam | Size | PSNR ↑ | SSIM ↑ | LPIPS ↓ |
|--------------|-----------------|------|--------|--------|---------|
| LGM [110]    | /               | 256  | 21.44  | 0.832  | 0.122   |
| GS-LRM [154] | ✓               | 256  | 29.59  | 0.944  | 0.051   |
| LVSM [53]    | ✓               | 256  | 31.71  | 0.957  | 0.027   |
| Ours-NVS*    | ×               | 224  | 30.41  | 0.949  | 0.033   |

Table 7. Quantitative comparisons for view synthesis on GSO [28] dataset. Finetuning VGGT for feed-forward novel view synthesis, it demonstrates competitive performance even without knowing camera extrinsic and intrinsic parameters for the input images. Note that \* indicates using a small training set (only 20%).

closely, e.g., using 4 input views and adopting Plücker rays to represent target viewpoints. We make a simple modification to VGGT. As before, the input images are converted into tokens by DINO. Then, for the target views, we use a convolutional layer to encode their Plücker ray images into tokens. These tokens, representing both the input images and the target views, are concatenated and processed by the AA transformer. Subsequently, a DPT head is used to regress the RGB colors for the target views. It is important to note that we do not input the Plücker rays for the source images. Hence, the model is not given the camera parameters for these input frames.

LVSM was trained on the Objaverse dataset [20]. We use a similar internal dataset of approximately 20% the size of Objaverse. Further details on training and evaluation can be found in [53]. As shown in Tab. 7, despite not requiring the input camera parameters and using less training data than LVSM, our model achieves competitive results on the GSO dataset [28]. We expect that better results would be obtained using a larger training dataset. Qualitative examples are shown in Fig. 6.

**Dynamic Point Tracking** has emerged as a highly competitive task in recent years [25, 44, 57, 136], and it serves as another downstream application for our learned features. Following standard practices, we report these point-tracking metrics: Occlusion Accuracy (OA), which comprises the binary accuracy of occlusion predictions;  $\delta_{\rm avg}^{\rm vis}$ , comprising the

<span id="page-9-2"></span><span id="page-9-0"></span>

| Method                                          | K                   | Cinetio                      | es   | RGB-S |                              |             | DAVIS |                              |      |
|-------------------------------------------------|---------------------|------------------------------|------|-------|------------------------------|-------------|-------|------------------------------|------|
|                                                 | AJ                  | $\delta_{\rm avg}^{\rm vis}$ | OA   | AJ    | $\delta_{\rm avg}^{\rm vis}$ | OA          | AJ    | $\delta_{\rm avg}^{\rm vis}$ | OA   |
| TAPTR [63]<br>LocoTrack [13]<br>BootsTAPIR [26] | 52.9                | 66.8                         | 85.3 | 69.7  | 76.2<br>83.2<br>83.0         | <u>89.5</u> | 62.9  | 75.3                         | 87.2 |
| CoTracker [56]<br>CoTracker + Ours              | 49.6<br><b>57.2</b> |                              |      |       |                              |             |       |                              |      |

Table 8. **Dynamic Point Tracking Results on the TAP-Vid benchmarks.** Although our model was not designed for dynamic scenes, simply fine-tuning CoTracker with our pretrained weights significantly enhances performance, demonstrating the robustness and effectiveness of our learned features.

mean proportion of visible points accurately tracked within a certain pixel threshold; and Average Jaccard (AJ), measuring tracking and occlusion prediction accuracy together.

We adapt the state-of-the-art CoTracker2 model [57] by substituting its backbone with our pretrained feature backbone. This is necessary because VGGT is trained on unordered image collections instead of sequential videos. Our backbone predicts the tracking features  $T_i$ , which replace the outputs of the feature extractor and later enter the rest of the CoTracker2 architecture, that finally predicts the tracks. We finetune the entire modified tracker on Kubric [41]. As illustrated in Tab. 8, the integration of pretrained VGGT significantly enhances CoTracker's performance on the TAP-Vid benchmark [23]. For instance, VGGT's tracking features improve the  $\delta_{\rm avg}^{\rm vis}$  metric from 78.9 to 84.0 on the TAP-Vid RGB-S dataset. Despite the TAP-Vid benchmark's inclusion of videos featuring rapid dynamic motions from various data sources, our model's strong performance demonstrates the generalization capability of its features, even in scenarios for which it was not explicitly designed.

### 5. Discussions

Limitations. While our method exhibits strong generalization to diverse in-the-wild scenes, several limitations remain. First, the current model does not support fisheye or panoramic images. Additionally, reconstruction performance drops under conditions involving extreme input rotations. Moreover, although our model handles scenes with minor non-rigid motions, it fails in scenarios involving substantial non-rigid deformation.

However, an important advantage of our approach is its flexibility and ease of adaptation. Addressing these limitations can be straightforwardly achieved by fine-tuning the model on targeted datasets with minimal architectural modifications. This adaptability clearly distinguishes our method from existing approaches, which typically require extensive re-engineering during test-time optimization to accommodate such specialized scenarios.

<span id="page-9-1"></span>

| Input Frames | 1    | 2    | 4    | 8    | 10   | 20   | 50    | 100   | 200   |
|--------------|------|------|------|------|------|------|-------|-------|-------|
| Time (s)     | 0.04 | 0.05 | 0.07 | 0.11 | 0.14 | 0.31 | 1.04  | 3.12  | 8.75  |
| Mem. (GB)    | 1.88 | 2.07 | 2.45 | 3.23 | 3.63 | 5.58 | 11.41 | 21.15 | 40.63 |

Table 9. Runtime and peak GPU memory usage across different numbers of input frames. Runtime is measured in seconds, and GPU memory usage is reported in gigabytes.

**Runtime and Memory.** As shown in Tab. 9, we evaluate inference runtime and peak GPU memory usage of the feature backbone when processing varying numbers of input frames. Measurements are conducted using a single NVIDIA H100 GPU with flash attention v3 [98]. Images have a resolution of  $336 \times 518$ .

We focus on the cost associated with the feature backbone since users may select different branch combinations depending on their specific requirements and available resources. The camera head is lightweight, typically accounting for approximately 5% of the runtime and about 2% of the GPU memory used by the feature backbone. A DPT head uses an average of 0.03 seconds and 0.2 GB GPU memory per frame.

When GPU memory is sufficient, multiple frames can be processed efficiently in a single forward pass. At the same time, in our model, inter-frame relationships are handled only within the feature backbone, and the DPT heads make independent predictions per frame. Therefore, users constrained by GPU resources may perform predictions frame by frame. We leave this trade-off to the user's discretion.

We recognize that a naive implementation of global selfattention can be highly memory-intensive with a large number of tokens. Savings or accelerations can be achieved by employing techniques used in large language model (LLM) deployments. For instance, Fast3R [141] employs Tensor Parallelism to accelerate inference with multiple GPUs, which can be directly applied to our model.

**Patchifying.** As discussed in Sec. 3.2, we have explored the method of patchifying images into tokens by utilizing either a  $14 \times 14$  convolutional layer or a pretrained DI-NOv2 model. Empirical results indicate that the DINOv2 model provides better performance; moreover, it ensures much more stable training, particularly in the initial stages. The DINOv2 model is also less sensitive to variations in hyperparameters such as learning rate or momentum. Consequently, we have chosen DINOv2 as the default method for patchifying in our model.

**Differentiable BA.** We also explored the idea of using differentiable bundle adjustment as in VGGSfM [125]. In small-scale preliminary experiments, differentiable BA demonstrated promising performance. However, a bottleneck is its computational cost during training. Enabling differentiable BA in PyTorch using Theseus [85] typically makes each training step roughly 4 times slower, which

<span id="page-10-2"></span>is expensive for large-scale training. While customizing a framework to expedite training could be a potential solution, it falls outside the scope of this work. Thus, we opted not to include differentiable BA in this work, but we recognize it as a promising direction for large-scale unsupervised training, as it can serve as an effective supervision signal in scenarios lacking explicit 3D annotations.

Single-view Reconstruction. Unlike systems like DUSt3R and MASt3R that have to duplicate an image to create a pair, our model architecture inherently supports the input of a single image. In this case, global attention simply transitions to frame-wise attention. Although our model was not explicitly trained for single-view reconstruction, it demonstrates surprisingly good results. Some examples can be found in Fig. [3](#page-3-3) and Fig. [7.](#page-12-7) We strongly encourage trying our demo for better visualization.

Normalizing Prediction. As discussed in Sec. [3.4,](#page-5-0) our approach normalizes the ground truth using the average Euclidean distance of the 3D points. While some methods, such as DUSt3R, also apply such normalization to network predictions, our findings suggest that it is neither necessary for convergence nor advantageous for final model performance. Furthermore, it tends to introduce additional instability during the training phase.

## 6. Conclusions

We present Visual Geometry Grounded Transformer (VGGT), a feed-forward neural network that can directly estimate all key 3D scene properties for hundreds of input views. It achieves state-of-the-art results in multiple 3D tasks, including camera parameter estimation, multiview depth estimation, dense point cloud reconstruction, and 3D point tracking. Our simple, neural-first approach departs from traditional visual geometry-based methods, which rely on optimization and post-processing to obtain accurate and task-specific results. The simplicity and efficiency of our approach make it well-suited for real-time applications, which is another benefit over optimization-based approaches.

# Appendix

In the Appendix, we provide the following:

- formal definitions of key terms in Appendix [A.](#page-10-0)
- comprehensive implementation details, including architecture and training hyperparameters in Appendix [B.](#page-10-1)
- additional experiments and discussions in Appendix [C.](#page-11-0)
- qualitative examples of single-view reconstruction in Appendix [D.](#page-11-1)
- an expanded review of related works in Appendix [E.](#page-11-2)

## <span id="page-10-0"></span>A. Formal Definitions

In this section, we provide additional formal definitions that further ground the method section.

The camera extrinsics are defined in relation to the *world reference frame*, which we take to be the coordinate system of the first camera. We thus introduce two functions. The first function γ(g, p) = p ′ applies the rigid transformation encoded by g to a point p in the world reference frame to obtain the corresponding point p ′ in the camera reference frame. The second function π(g, p) = y further applies perspective projection, mapping the 3D point p to a 2D image point y. We also denote the depth of the point as observed from the camera g by π <sup>D</sup>(g, p) = d ∈ R +.

We model the scene as a collection of regular surfaces S<sup>i</sup> ⊂ R 3 . We make this a function of the i-th input image as the scene can change over time [\[151\]](#page-18-19). The depth at pixel location y ∈ I(Ii) is defined as the minimum depth of any 3D point p in the scene that projects to y, *i.e*., Di(y) = min{π <sup>D</sup>(g<sup>i</sup> , p) : p ∈ S<sup>i</sup> ∧ π(g<sup>i</sup> , p) = y}. The point at pixel location y is then given by Pi(y) = γ(g, p), where p ∈ S<sup>i</sup> is the 3D point that minimizes the expression above, *i.e*., p ∈ S<sup>i</sup> ∧ π(g<sup>i</sup> , p) = y ∧ π <sup>D</sup>(g<sup>i</sup> , p) = Di(y).

## <span id="page-10-1"></span>B. Implementation Details

Architecture. As mentioned in the main paper, VGGT consists of 24 attention blocks, each block equipped with one frame-wise self-attention layer and one global selfattention layer. Following the ViT-L model used in DI-NOv2 [\[78\]](#page-15-1), each attention layer is configured with a feature dimension of 1024 and employs 16 heads. We use the official implementation of the attention layer from PyTorch, *i.e*., *torch.nn.MultiheadAttention*, with flash attention enabled. To stabilize training, we also use QKNorm [\[48\]](#page-14-21) and LayerScale [\[115\]](#page-17-21) for each attention layer. The value of LayerScale is initialized with 0.01. For image tokenization, we use DINOv2 [\[78\]](#page-15-1) and add positional embedding. As in [\[143\]](#page-18-20), we feed the tokens from the 4-th, 11-th, 17-th, and 23-rd block into DPT [\[87\]](#page-16-9) for upsampling.

Training. To form a training batch, we first choose a random training dataset (each dataset has a different yet approximately similar weight, as in [\[129\]](#page-17-1)), and from the <span id="page-11-4"></span>dataset, we then sample a random scene (uniformly). During the training phase, we select between 2 and 24 frames per scene while maintaining the constant total of 48 frames within each batch. For training, we use the respective training sets of each dataset. We exclude training sequences containing fewer than 24 frames. RGB frames, depth maps, and point maps are first isotropically resized, so the longer size has 518 pixels. Then, we crop the shorter dimension (around the principal point) to a size between 168 and 518 pixels while remaining a multiple of the 14-pixel patch size. It is worth mentioning that we apply aggressive color augmentation independently across each frame within the same scene, enhancing the model's robustness to varying lighting conditions. We build ground truth tracks following [33, 105, 125], which unprojects depth maps to 3D, reprojects points to target frames, and retains correspondences where reprojected depths match target depth maps. Frames with low similarity to the guery frame are excluded during batch sampling. In rare cases with no valid correspondences, the tracking loss is omitted.

### <span id="page-11-0"></span>C. Additional Experiments

Camera Pose Estimation on IMC We also evaluate using the Image Matching Challenge (IMC) [54], a camera pose estimation benchmark focusing on phototourism data. Until recently, the benchmark was dominated by classical incremental SfM methods [94].

**Baselines.** We evaluate two flavors of our model: VGGT and VGGT + BA. VGGT directly outputs camera pose estimates, while VGGT + BA refines the estimates using an additional Bundle Adjustment stage. We compare to the classical incremental SfM methods such as [66, 94] and to recently-proposed deep methods. Specifically, recently VGGSfM [125] provided the first end-to-end trained deep method that outperformed incremental SfM on the challenging phototourism datasets.

Besides VGGSfM, we additionally compare to recently popularized DUSt3R [129] and MASt3R [62]. It is important to note that DUSt3R and MASt3R utilized a substantial portion of the MegaDepth dataset for training, only excluding scenes 0015 and 0022. The MegaDepth scenes employed in their training have some overlap with the IMC benchmark, although the images are not identical; the same scenes are present in both datasets. For instance, the MegaDepth scene 0024 corresponds to the British Museum, while the British Museum is also a scene in the IMC benchmark. For an apples-to-apples comparison, we adopt the same training split as DUSt3R and MASt3R. In the main paper, to ensure a fair comparison on ScanNet-1500, we exclude the corresponding ScanNet scenes from our training.

**Results.** Table 10 contains the results of our evaluation. Although phototourism data is the traditional focus of SfM

<span id="page-11-3"></span>

| Method                  | Test-time Opt. | AUC@3° | AUC@5° | AUC@10°      | Runtime     |
|-------------------------|----------------|--------|--------|--------------|-------------|
| COLMAP (SIFT+NN) [94]   | 1              | 23.58  | 32.66  | 44.79        | >10s        |
| PixSfM (SIFT + NN) [66] | ✓              | 25.54  | 34.80  | 46.73        | >20s        |
| PixSfM (LoFTR) [66]     | ✓              | 44.06  | 56.16  | 69.61        | >20s        |
| PixSfM (SP + SG) [66]   | ✓              | 45.19  | 57.22  | 70.47        | >20s        |
| DFSfM (LoFTR) [47]      | /              | 46.55  | 58.74  | 72.19        | >10s        |
| DUSt3R [129]            | 1              | 13.46  | 21.24  | 35.62        | ~ 7s        |
| MASt3R [62]             | ✓              | 30.25  | 46.79  | 57.42        | $\sim 9s$   |
| VGGSfM [125]            | ✓              | 45.23  | 58.89  | 73.92        | $\sim 6s$   |
| VGGSfMv2 [125]          | /              | 59.32  | 67.78  | <u>76.82</u> | $\sim 10 s$ |
| VGGT (ours)             | х              | 39.23  | 52.74  | 71.26        | 0.2s        |
| VGGT + BA (ours)        | /              | 66.37  | 75.16  | 84.91        | 1.8s        |

Table 10. Camera Pose Estimation on IMC [54]. Our method achieves state-of-the-art performance on the challenging phototropism data, outperforming VGGSfMv2 [125] which ranked first on the latest CVPR'24 IMC Challenge in camera pose (rotation and translation) estimation.

methods, our VGGT's feed-forward performance is on par with the state-of-the-art VGGSfMv2 with AUC@10 of 71.26 versus 76.82, while being significantly faster (0.2 vs. 10 seconds per scene). Remarkably, VGGT outperforms both MASt3R [62] and DUSt3R [129] significantly across all accuracy thresholds while being much faster. This is because MASt3R's and DUSt3R's feed-forward predictions can only process pairs of frames and, hence, require a costly global alignment step. Additionally, with bundle adjustment, VGGT + BA further improves drastically, achieving state-of-the-art performance on IMC, raising AUC@10 from 71.26 to 84.91, and raising AUC@3 from 39.23 to 66.37. Note that our model directly predicts 3D points, which can serve as the initialization for BA. This eliminates the need for triangulation and iterative refinement of BA as in [125]. As a result, VGGT + BA is much faster than [125].

#### <span id="page-11-1"></span>**D.** Qualitative Examples

We further present qualitative examples of single-view reconstruction in Fig. 7.

### <span id="page-11-2"></span>E. Related Work

In this section, we discuss additional related works.

**Vision Transformers.** The Transformer architecture was initially proposed for language processing tasks [6, 22, 120]. It was later introduced to the computer vision community by ViT [27], sparking widespread adoption. Vision Transformers and their variants have since become dominant in the design of architectures for various computer vision tasks [4, 12, 83, 137], thanks to their simplicity, high capacity, flexibility, and ability to capture long-range dependencies.

DeiT [114] demonstrated that Vision Transformers can be effectively trained on datasets like ImageNet using strong data augmentation strategies. DINO [10] revealed

<span id="page-12-11"></span><span id="page-12-7"></span>![](_page_12_Picture_0.jpeg)

Figure 7. Single-view Reconstruction by Point Map Estimation. Unlike DUSt3R, which requires duplicating an image into a pair, our model can predict the point map from a single input image. It demonstrates strong generalization to unseen real-world images.

intriguing properties of features learned by Vision Transformers in a self-supervised manner. CaiT [\[115\]](#page-17-21) introduced layer scaling to address the challenges of training deeper Vision Transformers, effectively mitigating gradient-related issues. Further, techniques such as QKNorm [\[48,](#page-14-21) [150\]](#page-18-22) have been proposed to stabilize the training process. Additionally, [\[138\]](#page-18-23) also explores the dynamics between frame-wise and global attention modules in object tracking, though using cross-attention.

Camera Pose Estimation. Estimating camera poses from multi-view images is a crucial problem in 3D computer vision. Over the last decades, Structure from Motion (SfM) has emerged as the dominant approach [\[46\]](#page-14-24), whether incremental [\[2,](#page-12-2) [36,](#page-14-3) [94,](#page-16-1) [103,](#page-16-2) [134\]](#page-18-2) or global [\[3,](#page-12-10) [14–](#page-13-16)[17,](#page-13-17) [52,](#page-14-25) [73,](#page-15-23) [79,](#page-15-24) [81,](#page-15-25) [90,](#page-16-20) [106\]](#page-16-21). Recently, a set of methods treat camera pose estimation as a regression problem [\[65,](#page-15-26) [100,](#page-16-22) [109,](#page-17-5) [112,](#page-17-6) [113,](#page-17-7) [118,](#page-17-8) [122,](#page-17-9) [123,](#page-17-24) [131,](#page-17-10) [152,](#page-18-24) [153,](#page-18-25) [160\]](#page-19-0), which show promising results under the sparse-view setting. Ace-Zero [\[5\]](#page-12-3) further proposes to regress 3D scene coordinates and FlowMap [\[101\]](#page-16-23) focuses on depth maps, as intermediates for camera prediction. Instead, VGGSfM [\[125\]](#page-17-0) simplifies the classical SfM pipeline to a differentiable framework, demonstrating exceptional performance, particularly with phototourism datasets. At the same time, DUSt3R [\[62,](#page-15-0) [129\]](#page-17-1) introduces an approach to learn pixel-aligned point map, and hence camera poses can be recovered by simple alignment. This paradigm shift has garnered considerable interest as the point map, an over-parameterized representation, offers seamless integration with various downstream applications, such as 3D Gaussian splatting.