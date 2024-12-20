// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

import { createStore as _createStore } from 'vuex'
import state from './state'
import mutations from './mutations'
import actions from './actions'
import createPersistedState from "vuex-persistedstate";


export default new _createStore({
  state,
  mutations,
  actions,
  plugins: [createPersistedState({
    paths: ['execution_history']
  })]
})
