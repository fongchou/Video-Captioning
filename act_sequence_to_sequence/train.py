from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import sys
import numpy as np
from six.moves import xrange  # pylint: disable=redefined-builtin
import tensorflow as tf
import cPickle
from config import *
from model import Seq2Seq

def create_model(session, forward_only, step=None):
  model = Seq2Seq(FLAGS.num_units, FLAGS.use_lstm, FLAGS.epsilon, FLAGS.max_computation, FLAGS.encoder_max_sequence_length, FLAGS.decoder_max_sentence_length, FLAGS.feature_size, FLAGS.vocab_size, FLAGS.learning_rate, FLAGS.learning_rate_decay_factor, FLAGS.time_penalty, FLAGS.max_gradient_norm, forward_only)
  ckpt = tf.train.get_checkpoint_state(FLAGS.checkpoint_dir)
  if ckpt and tf.train.checkpoint_exists(ckpt.model_checkpoint_path):
    if step == None:
      print("Reading model parameters from %s" % ckpt.model_checkpoint_path)
      model.saver.restore(session, ckpt.model_checkpoint_path)
    else:
      ckpt_path = os.path.join(FLAGS.checkpoint_dir,'ckpt-%d'%step)
      print("Reading model parameters from %s" % ckpt_path)
      model.saver.restore(session, ckpt_path)
  else:
    print("Created model with fresh parameters.")
    session.run(tf.global_variables_initializer())
  return model

def train():
  with open (os.path.join(FLAGS.data_dir, 'feature.train'), 'rb') as f:
    feature = cPickle.load(f)
  with open (os.path.join(FLAGS.data_dir, 'caption.train'), 'rb') as f:
    sentence = cPickle.load(f)

  with tf.Session() as sess:
    model = create_model(sess, False)
    previous_losses = []
    current_step = 0
    while current_step <= 10000:
      np.random.shuffle(sentence)
      for start,end in zip(range(0, len(sentence), FLAGS.batch_size), range(FLAGS.batch_size, len(sentence), FLAGS.batch_size)):
        feature_inputs, batch_decoder_inputs, batch_weights = model.get_batch(feature, sentence[start:end])
        loss1, loss2, remainders, iterations = model.step(sess, feature_inputs, batch_decoder_inputs, batch_weights, False)
        current_step += 1
        if current_step % FLAGS.steps_per_checkpoint == 0:
          R = ['%.3f'%remainders[j][0] for j in xrange(FLAGS.encoder_max_sequence_length)]
          I = ['%d'%iterations[j][0] for j in xrange(FLAGS.encoder_max_sequence_length)]
          print(' '.join(R))
          print(' '.join(I))
          print ("global step %d - learning rate %f - loss1 %.3f - loss2 %f" % (model.global_step.eval(), model.learning_rate.eval(), loss1, loss2 / FLAGS.time_penalty))
          checkpoint_path = os.path.join(FLAGS.checkpoint_dir, 'ckpt')
          model.saver.save(sess, checkpoint_path, global_step=model.global_step)
          sys.stdout.flush()
          if len(previous_losses) > 2 and loss1 > max(previous_losses[-3:]):
            sess.run(model.learning_rate_decay_op)
          previous_losses.append(loss1)

if __name__ == "__main__":
  train()
