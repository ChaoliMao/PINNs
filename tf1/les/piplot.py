# Inverse-PINN with for channel flow
# Data is retrieved in get_data.py

# -*- coding: utf-8 -*-

# Tensorflow version: 1.14
# Python version: 3.7.*

# Disables warnings
import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)

import tensorflow as tf
import numpy as np
import sys
from   mod import *
from   pylab import *
from   dom import Run, implot

tf.compat.v1.disable_eager_execution()

# Get parameters
# params = Run(sys.argv[1])
which = "03"
params = Run(which)

# -----------------------------------------------------------------------------
# Create the Neural Network 
# -----------------------------------------------------------------------------

# Here we create the NN, both the data part and the physics informed part. We
# also define the loss function and the optimizer, start the session, and
# initialize the variables.

# Shape of the NN
layers = [4]+[params.hu]*params.layers+[4]
L      = len(layers)

# Neurons
weights = ([xavier_init([layers[l], layers[l+1]])
            for l in range(0, L-1)])
biases  = ([tf.Variable(tf.zeros((1, layers[l+1]),dtype=tf.float64))
            for l in range(0, L-1)])


# Points where the data contraints are going to be imposed
t_u = tf.compat.v1.placeholder(tf.float64, shape=(None,1))
x_u = tf.compat.v1.placeholder(tf.float64, shape=(None,1))
y_u = tf.compat.v1.placeholder(tf.float64, shape=(None,1))
z_u = tf.compat.v1.placeholder(tf.float64, shape=(None,1))
field_u,_ = DNN(tf.concat((t_u,x_u,y_u,z_u),axis=1), layers, weights, biases)
u_u = field_u[:,0:1]
v_u = field_u[:,1:2]
w_u = field_u[:,2:3]
p_u = field_u[:,3:]

u_obs = tf.compat.v1.placeholder(tf.float64, shape=(None,1))
v_obs = tf.compat.v1.placeholder(tf.float64, shape=(None,1))
w_obs = tf.compat.v1.placeholder(tf.float64, shape=(None,1))

# Loss function for data constraints
loss_u = (tf.reduce_mean(tf.square(u_u-u_obs)) +
          tf.reduce_mean(tf.square(v_u-v_obs)) +
          tf.reduce_mean(tf.square(w_u-w_obs)))

# Points where the dynamical contraints are going to be imposed
t_f = tf.compat.v1.placeholder(tf.float64, shape=(None,1))
x_f = tf.compat.v1.placeholder(tf.float64, shape=(None,1))
y_f = tf.compat.v1.placeholder(tf.float64, shape=(None,1))
z_f = tf.compat.v1.placeholder(tf.float64, shape=(None,1))
field_f,_ = DNN(tf.concat((t_f,x_f,y_f,z_f),axis=1), layers, weights, biases)
u_f = field_f[:,0:1]
v_f = field_f[:,1:2]
w_f = field_f[:,2:3]
p_f = field_f[:,3:]

# Automatic differentiation and eqs
u_t = tf.gradients(u_f, t_f)[0]
v_t = tf.gradients(v_f, t_f)[0]
w_t = tf.gradients(w_f, t_f)[0]

u_x = tf.gradients(u_f, x_f)[0]
u_y = tf.gradients(u_f, y_f)[0]
u_z = tf.gradients(u_f, z_f)[0]

v_x = tf.gradients(v_f, x_f)[0]
v_y = tf.gradients(v_f, y_f)[0]
v_z = tf.gradients(v_f, z_f)[0]

w_x = tf.gradients(w_f, x_f)[0]
w_y = tf.gradients(w_f, y_f)[0]
w_z = tf.gradients(w_f, z_f)[0]

p_x = tf.gradients(p_f, x_f)[0]
p_y = tf.gradients(p_f, y_f)[0]
p_z = tf.gradients(p_f, z_f)[0]

u_xx = tf.gradients(u_x, x_f)[0]
u_yy = tf.gradients(u_y, y_f)[0]
u_zz = tf.gradients(u_z, z_f)[0]

v_xx = tf.gradients(v_x, x_f)[0]
v_yy = tf.gradients(v_y, y_f)[0]
v_zz = tf.gradients(v_z, z_f)[0]

w_xx = tf.gradients(w_x, x_f)[0]
w_yy = tf.gradients(w_y, y_f)[0]
w_zz = tf.gradients(w_z, z_f)[0]

S11 = u_x
S12 = 0.5*(u_y+v_x)
S13 = 0.5*(u_z+w_x)
S22 = v_y
S23 = 0.5*(v_z+w_y)
S33 = w_z

vl    = 1.006e-3
delta = 40*vl
# c_s   = tf.exp(tf.Variable(np.random.random(), dtype=tf.float64))
c_s   = tf.Variable(np.random.random(), dtype=tf.float64)
eddy_viscosity = (c_s*delta)**2*tf.sqrt(2*(S11**2+2*S12**2+2*S13**2+
                                                    S22**2+2*S23**2+
                                                             S33**2))
tau11 = -2*eddy_viscosity*S11
tau12 = -2*eddy_viscosity*S12
tau13 = -2*eddy_viscosity*S13
tau22 = -2*eddy_viscosity*S22
tau23 = -2*eddy_viscosity*S23
tau33 = -2*eddy_viscosity*S33

tau11_x = tf.gradients(tau11, x_f)[0]
tau12_y = tf.gradients(tau12, y_f)[0]
tau13_z = tf.gradients(tau13, z_f)[0]

tau21_x = tf.gradients(tau12, x_f)[0]
tau22_y = tf.gradients(tau22, y_f)[0]  
tau23_z = tf.gradients(tau23, z_f)[0]  

tau31_x = tf.gradients(tau13, x_f)[0]
tau32_y = tf.gradients(tau23, y_f)[0]  
tau33_z = tf.gradients(tau33, z_f)[0]  

# Equations to be enforced
nu = 5e-5
f0 = u_x+v_y+w_z
f1 = (u_t + u_f*u_x + v_f*u_y + w_f*u_z +
        p_x - nu*(u_xx+u_yy+u_zz) + tau11_x + tau12_y + tau13_z)
f2 = (v_t + u_f*v_x + v_f*v_y + w_f*v_z +
        p_y - nu*(v_xx+v_yy+v_zz) + tau21_x + tau22_y + tau23_z)
f3 = (w_t + u_f*w_x + v_f*w_y + w_f*w_z +
        p_z - nu*(w_xx+w_yy+w_zz) + tau31_x + tau32_y + tau33_z)

# Loss function for dynamical constraints
lfw = tf.Variable(params.lfw, trainable=False, dtype=tf.float64)
loss_f = lfw*(tf.reduce_mean(tf.square(f0)) +
              tf.reduce_mean(tf.square(f1)) +
              tf.reduce_mean(tf.square(f2)) +
              tf.reduce_mean(tf.square(f3)))
loss_f0 = tf.reduce_mean(tf.square(f0))
loss_f1 = tf.reduce_mean(tf.square(f1))
loss_f2 = tf.reduce_mean(tf.square(f2))
loss_f3 = tf.reduce_mean(tf.square(f3))

# Total loss function
loss = loss_f + loss_u

# Optimizer
optimizer = tf.compat.v1.train.AdamOptimizer(5.0e-4).minimize(loss)

# Create save object
saver = tf.compat.v1.train.Saver()

# Run Tensorflow session
sess = tf.compat.v1.Session()

# Restore session 
saver.restore(sess, "{}/session".format(which))

# Points for plotting
Nx = 56
Ny = 10
Nz = 56
visc_length = 1.0006e-3
dt          = 0.0065
dx          = 8*np.pi/2048
dz          = 3*np.pi/1536 
dx_plus     = dx/visc_length*2
dz_plus     = dz/visc_length*4
for tidx in [0,70,149]:
    t_p, x_p, y_p, z_p = plot_points(Nx, Ny, Nz, tidx=tidx)

    # Save fields
    u_p, v_p, w_p, p_p = sess.run([u_u,v_u,w_u,p_u],
                                  feed_dict={t_u: t_p,
                                             x_u: x_p,
                                             y_u: y_p,
                                             z_u: z_p})
    u_p = u_p.reshape(Nx,Ny,Nz)
    v_p = v_p.reshape(Nx,Ny,Nz)
    w_p = w_p.reshape(Nx,Ny,Nz)
    p_p = p_p.reshape(Nx,Ny,Nz)

    # Real fields
    vv = np.load("data/filt_velos.{:02}.npy".format(tidx))

    fig = figure(figsize=(20,10))

    fig.suptitle('$t={:.2f},\; \lambda = {}, \; d={}$'.format(tidx*dt,
                                                     params.lfw,
                                                     params.layers),
            fontsize=20)

    subplot(231)
    implot(vv[0,:,5,:], extent=[0,dx_plus*32,0,dz_plus*32])
    title('Real $u$')
    ylabel('$z^+$')
    subplot(232)
    implot(vv[1,:,5,:], extent=[0,dx_plus*32,0,dz_plus*32])
    title('Real $v$')
    subplot(233)
    implot(vv[2,:,5,:], extent=[0,dx_plus*32,0,dz_plus*32])
    title('Real $w$')

    subplot(234)
    implot(u_p[:,5,:], extent=[0,dx_plus*32,0,dz_plus*32])
    title('PINN $u$')
    ylabel('$z^+$')
    xlabel('$x^+$')
    subplot(235)
    implot(v_p[:,5,:], extent=[0,dx_plus*32,0,dz_plus*32])
    title('PINN $v$')
    xlabel('$x^+$')
    subplot(236)
    implot(w_p[:,5,:], extent=[0,dx_plus*32,0,dz_plus*32])
    title('PINN $w$')
    xlabel('$x^+$')

    savefig("comp{}_{:03}".format(which,tidx))

draw()
show()
