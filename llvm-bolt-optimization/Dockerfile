FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential cmake ninja-build git ca-certificates python3 lld \
    binutils time linux-tools-generic && rm -rf /var/lib/apt/lists/*
WORKDIR /project
COPY . /project
ARG JOBS=2
RUN WORK=/opt/bolt-small-layout JOBS=${JOBS} bash scripts/build.sh \
    && /opt/bolt-small-layout/build/bin/llvm-bolt --help | grep small-function-layout
ENV BOLT=/opt/bolt-small-layout/build/bin/llvm-bolt
ENV WORK=/tmp/bolt-experiments
CMD ["bash", "scripts/run_all.sh"]
