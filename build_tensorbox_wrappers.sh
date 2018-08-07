UUID=$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 32 | head -n 1)

BUILD_DIR=/tmp/$UUID
CWD=$(pwd)
SHA_COMMIT=9596fe5408cedb1c894409ffb647d100864c7008
GIT_REPO=git@github.com:BossaNova/TensorBox.git
VENV=/opt/virtualenvs/build

mkdir -p $BUILD_DIR && cd $BUILD_DIR

git clone $GIT_REPO
cd TensorBox
git checkout $SHA_COMMIT
cd utils
. $VENV/bin/activate
export LD_LIBRARY_PATH=/usr/local/cuda-8.0/lib64${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}
make && make hungarian
cd ..
# python $CWD/tests/wrappers/test_hungarian_module.py
cp utils/hungarian/hungarian.so $CWD/app/utils/hungarian/hungarian.so
cp utils/stitch_wrapper.so $CWD/app/utils/stitch_wrapper.so
cp utils/rect.py $CWD/app/utils/rect.py
