/*
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
*/

export default {
  updateAssetId (state, value) {
    state.display_asset_id = value
  },
  updatePlayer (state, player) {
    state.player = player
  },
  updateTimeseries (state, value){
    state.chart_tuples = value
  },
  updateCurrentTime (state, value) {
    state.current_time = value
  },
  updateSelectedLabel (state, value){
    state.selected_label = value
  },
  updateExecutedAssets (state, value){
    state.execution_history = value
  },
  updateWaveformSeekPosition (state, value){
    state.waveform_seek_position = value
  },
  updateOperatorInfo (state, value){
    state.operator_info = value
  },
  updateUnsavedCustomVocabularies (state, value){
    state.unsaved_custom_vocabularies = value
  },
}
