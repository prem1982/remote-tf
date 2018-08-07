import tensorflow as tf

class HungarianModule(tf.test.TestCase):
  def testZeroOut(self):
    hungarian = tf.load_op_library('utils/hungarian/hungarian.so')
    with self.test_session():
      result = hungarian.hungarian(1,1,2,3)
      print result
      self.assertIsNotNone(result)

if __name__ == "__main__":
  tf.test.main()
