import tensorflow as tf
import numpy as np
import scipy.misc
import scipy.io
import sys
import time
import os
from model import vgg19_pretrained

# style conversion parameters
INIT_NOISE_RATIO = 0.3
STYLE_STRENGTH = 100
ITERATION = 5000

# mean by ImageNet
MEAN_VALUES = np.array([123, 117, 104]).reshape((1, 1, 1, 3))


def build_content_loss(p, x):
    square = p.shape[1] * p.shape[2]
    ch = p.shape[3]
    loss = (1. / (2 * ch ** 0.5 * square ** 0.5)) * tf.reduce_sum(tf.pow((x - p), 2))
    return loss


def gram_matrix(x, area, depth):
    x1 = tf.reshape(x, (area, depth))
    g = tf.matmul(tf.transpose(x1), x1)
    return g


def gram_matrix_val(x, area, depth):
    x1 = x.reshape(area, depth)
    g = np.dot(x1.T, x1)
    return g


def build_style_loss(a, x):
    m = a.shape[1] * a.shape[2]
    n = a.shape[3]
    a = gram_matrix_val(a, m, n)
    g = gram_matrix(x, m, n)
    loss = (1. / (4 * n ** 2 * m ** 2)) * tf.reduce_sum(tf.pow((g - a), 2))
    return loss


def reshape_images(images, shape):
    resize_image = []
    for image in images:
        image = scipy.misc.imresize(image, shape)
        image = image[np.newaxis, :, :, :]
        image = image - MEAN_VALUES
        resize_image.append(image)
    return resize_image


def write_image(path, image):
    image = image + MEAN_VALUES
    image = image[0]
    image = np.clip(image, 0, 255).astype('uint8')
    scipy.misc.imsave(path, image)


def main():
    if len(sys.argv) < 3:
        print('execute as below')
        print('\'python {} [content-image-format] [style-image-format] [result-image-format(optional)]'
              ' [process-output-bool(optional)]\''.format(os.path.basename(__file__)))
        exit('argument Error')

    content_img_path = sys.argv[1]
    style_img_path = sys.argv[2]

    output_dir = 'results'
    if len(sys.argv) < 4:
        output_img_path = 'result.png'
    else:
        output_img_path = sys.argv[3]

    if len(sys.argv) < 5:
        process_output = False
    else:
        process_output = bool(int(sys.argv[4]))

    print('Content: {}, Style: {}'.format(content_img_path, style_img_path))
    print('Results will be saved as {}'.format(output_dir + '/' + output_img_path))

    # read and reshape images
    content_img = scipy.misc.imread(content_img_path)
    style_img = scipy.misc.imread(style_img_path)
    input_shape = (content_img.shape[0], content_img.shape[1])
    [content_img, style_img] = reshape_images([content_img, style_img], input_shape)

    # construct vgg19-network
    net = vgg19_pretrained(input_shape)
    noise_img = np.random.uniform(-20, 20, (1, input_shape[0], input_shape[1], 3)).astype(np.float32)

    init = tf.global_variables_initializer()
    sess = tf.Session()
    sess.run(init)

    content_feature_layers = [('conv4_2', 1.)]
    style_feature_layers = [('conv1_1', 1.), ('conv2_1', 1.), ('conv3_1', 1.), ('conv4_1', 1.), ('conv5_1', 1.)]

    # content net
    sess.run([net['input'].assign(content_img)])
    cost_content = sum(map(lambda l: l[1] * build_content_loss(sess.run(net[l[0]]), net[l[0]]), content_feature_layers))

    # style net
    sess.run([net['input'].assign(style_img)])
    cost_style = sum(map(lambda l: l[1] * build_style_loss(sess.run(net[l[0]]), net[l[0]]), style_feature_layers))

    cost_total = cost_content + STYLE_STRENGTH * cost_style
    optimizer = tf.train.AdamOptimizer(2.0)

    train = optimizer.minimize(cost_total)
    sess.run(tf.global_variables_initializer())
    sess.run([net['input'].assign(INIT_NOISE_RATIO * noise_img + (1. - INIT_NOISE_RATIO) * content_img)])

    if not os.path.exists(output_dir):
        os.mkdir(output_dir)

    start = time.perf_counter()
    for i in range(ITERATION):
        sess.run(train)
        if i % 100 == 0:
            result_img = sess.run(net['input'])
            elapsed = time.perf_counter() - start
            print('ITERATION: ', i, ', ', sess.run(cost_total), ', elapsed: ', elapsed, '[sec]')
            if process_output:
                write_image(os.path.join(output_dir, '%s.png' % (str(i).zfill(4))), result_img)
            start = time.perf_counter()

    write_image(os.path.join(output_dir, output_img_path), result_img)


if __name__ == '__main__':
    main()
    print('finish')
