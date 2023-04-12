<!-- 
######################################################################################################################
#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.                                                #
#                                                                                                                    #
#  Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance    #
#  with the License. A copy of the License is located at                                                             #
#                                                                                                                    #
#      http://www.apache.org/licenses/LICENSE-2.0                                                                    #
#                                                                                                                    #
#  or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES #
#  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions    #
#  and limitations under the License.                                                                                #
######################################################################################################################
-->

<template>
  <b-container fluid>
    <b-img id="imageFeature" fluid :src="image_url" @load="onImageLoad"></b-img>
    <canvas
      id="canvas"
      class="canvas"
    />
  </b-container>
</template>

<script>
export default {
  name: 'ImageFeature',
  props: {
    options: {
      type: Object,
      default() {
        return {};
      }
    }
  },
  data: function () {
    return {
      image_url: '',
    }
  },
  beforeDestroy() {
  },
  created() {
    const _image_url = this.options.sources[0].src;
    this.image_url = _image_url
  },
  mounted: function () {
    window.addEventListener('resize', function () {
      // Update canvas size when window is resized
      let canvas = document.getElementById('canvas');
      let image_feature = document.getElementById('imageFeature');
      canvas.width = image_feature.clientWidth;
      canvas.height = image_feature.clientHeight;
    });
  },
  methods: {
    onImageLoad() {
      // Set canvas size to videoPlayer size
      let canvas = document.getElementById('canvas');
      let image_feature = document.getElementById('imageFeature');
      canvas.width = image_feature.clientWidth;
      canvas.height = image_feature.clientHeight;
    },
  },
}
</script>

<style scoped>
  .canvas {
    position: absolute;
    top: 0;
    left: 30px;
    /*background-color:rgba(255,0,0,0.5);*/
    pointer-events: none;
  }
</style>
