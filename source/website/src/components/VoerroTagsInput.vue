<!-- 
  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
  SPDX-License-Identifier: Apache-2.0
-->

<template>
  <div class="tags-input-root" style="position: relative;">
    <div
      :class="{
        [wrapperClass + ' tags-input']: true,
        'active': isActive,
      }"
    >
      <span
        v-for="(tag, index) in tags"
        :key="index"
        class="tags-input-badge tags-input-badge-pill tags-input-badge-selected-default"
      >
        <span v-text="tag.value"></span>

        <a
          href="#"
          class="tags-input-remove"
          @click.prevent="removeTag(index)"
        ></a>
      </span>
      <p>
        <input
          v-show="!hideInputField"
          ref="taginput"
          v-model="input"
          type="text"
          :placeholder="placeholder"
          @keydown.enter.prevent="tagFromInput(false)"
          @keydown.8="removeLastTag"
          @keydown.down="nextSearchResult"
          @keydown.up="prevSearchResult"
          @keydown="onKeyDown"
          @keyup="onKeyUp"
          @keyup.esc="clearSearchResults"
          @focus="onFocus"
          @click="onClick"
          @blur="onBlur"
          @value="tags"
        >
      </p>

      <input
        v-if="elementId" :id="elementId"
        v-model="hiddenInput"
        type="hidden"
        :name="elementId"
      >
    </div>
    <b-alert
      :show="hideInputField"
      variant="warning"
    >
      Pick no more than 10.
    </b-alert>

    <!-- Typeahead/Autocomplete -->
    <div v-show="searchResults.length">
      <p v-if="typeaheadStyle === 'badges'" :class="`typeahead-${typeaheadStyle}`">
        <span
          v-if="!typeaheadHideDiscard" class="tags-input-badge typeahead-hide-btn tags-input-typeahead-item-default"
          @click.prevent="clearSearchResults(true)"
          v-text="discardSearchText"
        ></span>

        <span
          v-for="(tag, index) in searchResults"
          :key="index"
          class="tags-input-badge"
          :class="{
            'tags-input-typeahead-item-default': index != searchSelection,
            'tags-input-typeahead-item-highlighted-default': index == searchSelection
          }"
          @mouseover="searchSelection = index"
          @mousedown.prevent="tagFromSearchOnClick(tag)"
          v-text="tag.value"
        ></span>
      </p>

      <ul v-else-if="typeaheadStyle === 'dropdown'" :class="`typeahead-${typeaheadStyle}`">
        <li
          v-if="!typeaheadHideDiscard" class="tags-input-typeahead-item-default typeahead-hide-btn"
          @click.prevent="clearSearchResults(true)"
          v-text="discardSearchText"
        ></li>

        <li
          v-for="(tag, index) in searchResults"
          :key="index"
          :class="{
            'tags-input-typeahead-item-default': index != searchSelection,
            'tags-input-typeahead-item-highlighted-default': index == searchSelection
          }"
          @mouseover="searchSelection = index"
          @mousedown.prevent="tagFromSearchOnClick(tag)"
          v-text="tag.value"
        ></li>
      </ul>
    </div>
  </div>
</template>

<script>
export default {
    props: {
        elementId: {
          type: String,
          default: () => {
            return "";
          }
        },

        existingTags: {
            type: Array,
            default: () => {
                return [];
            }
        },

        value: {
            type: Array,
            default: () => {
                return [];
            }
        },

        typeahead: {
            type: Boolean,
            default: false
        },

        typeaheadStyle: {
            type: String,
            default: 'badges'
        },

        typeaheadActivationThreshold: {
            type: Number,
            default: 1
        },

        typeaheadMaxResults: {
            type: Number,
            default: 0
        },

        typeaheadAlwaysShow: {
            type: Boolean,
            default: false
        },

        typeaheadShowOnFocus: {
            type: Boolean,
            default: true
        },

        typeaheadHideDiscard: {
            type: Boolean,
            default: false
        },

        typeaheadUrl: {
            type: String,
            default: ''
        },

        placeholder: {
            type: String,
            default: 'Type or select'
        },

        discardSearchText: {
            type: String,
            default: 'Discard Search Results'
        },

        limit: {
            type: Number,
            default: 0
        },

        hideInputOnLimit: {
            type: Boolean,
            default: false
        },

        onlyExistingTags: {
            type: Boolean,
            default: false
        },

        deleteOnBackspace: {
            type: Boolean,
            default: true
        },

        allowDuplicates: {
            type: Boolean,
            default: false
        },

        validate: {
            type: Function,
            default: () => true
        },

        addTagsOnComma: {
            type: Boolean,
            default: false
        },

        addTagsOnSpace: {
            type: Boolean,
            default: false
        },

        addTagsOnBlur: {
            type: Boolean,
            default: false
        },

        wrapperClass: {
            type: String,
            default: 'tags-input-wrapper-default'
        },

        sortSearchResults: {
            type: Boolean,
            default: true
        },

        caseSensitiveTags: {
            type: Boolean,
            default: false
        },

        beforeAddingTag: {
            type: Function,
            default: () => true
        },

        beforeRemovingTag: {
            type: Function,
            default: () => true
        },
    },

    data() {
        return {
            badgeId: 0,
            tags: [],

            input: '',
            oldInput: '',
            hiddenInput: '',

            searchResults: [],
            searchSelection: 0,

            selectedTag: -1,

            isActive: false,
        };
    },

    computed: {
        hideInputField() {
            return (this.hideInputOnLimit && this.limit > 0 && this.tags.length >= this.limit);
        }
    },

    watch: {
        input(newVal, oldVal) {
            this.searchTag(false);

            if (newVal.length && newVal != oldVal) {

                if (this.addTagsOnSpace) {
                    if (newVal.endsWith(' ')) {
                        // The space shouldn't actually be inserted
                        this.input = newVal.trim();

                        // Add the inputed tag
                        this.tagFromInput(true);
                    }
                }

                if (this.addTagsOnComma) {
                    newVal = newVal.trim();

                    if (newVal.endsWith(',')) {
                        // The comma shouldn't actually be inserted
                        this.input = newVal.substring(0, newVal.length - 1);

                        // Add the inputed tag
                        this.tagFromInput(true);
                    }
                }

                this.$emit('change', newVal);
            }
        },

        tags() {
            // Updating the hidden input
            this.hiddenInput = JSON.stringify(this.tags);

            // Update the bound v-model value
            this.$emit('input', this.tags);
        },

        value() {
            this.tagsFromValue();
        },

        typeaheadAlwaysShow(newValue) {
            if (newValue) {
                this.searchTag(false);
            } else {
                this.clearSearchResults();
            }
        },
    },

    created () {
        this.tagsFromValue();

        if (this.typeaheadAlwaysShow) {
            this.searchTag(false);
        }
    },

    mounted () {
        // Emit an event
        this.$emit('initialized');

        document.addEventListener('click', (e) => {
            if (e.target !== this.$refs['taginput']) {
                this.clearSearchResults();
            }
        });
    },

    methods: {
        /**
         * Remove reserved regex characters from a string so that they don't
         * affect search results
         *
         * @param string
         * @returns String
         */
        escapeRegExp(string) {
            return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        },

        /**
         * Add a tag whether from user input or from search results (typeahead)
         *
         * @param ignoreSearchResults
         * @returns void
         */
        tagFromInput(ignoreSearchResults = false) {
            // If we're choosing a tag from the search results
            if (this.searchResults.length && this.searchSelection >= 0 && !ignoreSearchResults) {
                this.tagFromSearch(this.searchResults[this.searchSelection]);

                this.input = '';
            }
            // If we're adding an unexisting tag
            let text = this.input.trim();

            // If the new tag is not an empty string and passes validation
            if (!this.onlyExistingTags && text.length && this.validate(text)) {
                this.input = '';

                // Determine if the inputted tag exists in the existingTags
                // array
                let newTag = {
                    key: '',
                    value: text,
                };

                const searchQuery = this.escapeRegExp(
                    this.caseSensitiveTags
                        ? newTag.value
                        : newTag.value.toLowerCase()
                );

                for (let tag of this.existingTags) {
                    const compareable = this.caseSensitiveTags
                        ? tag.value
                        : tag.value.toLowerCase();

                    if (searchQuery === compareable) {
                        newTag = Object.assign({}, tag);

                        break;
                    }
                }

                this.addTag(newTag);
            }
        },

        /**
         * Add a tag from search results when a user clicks on it
         *
         * @param tag
         * @returns void
         */
        tagFromSearchOnClick(tag) {
            this.tagFromSearch(tag);

            this.$refs['taginput'].blur();
        },

        /**
         * Add the selected tag from the search results.
         * Clear search results.
         * Clear user input.
         *
         * @param tag
         * @return void
         */
        tagFromSearch(tag) {
            this.clearSearchResults();
            this.addTag(tag);

            this.$nextTick(() => {
                this.input = '';
                this.oldInput = '';
            });
        },

        /**
         * Add/Select a tag
         *
         * @param tag
         * @returns void | Boolean
         */
        addTag(tag) {
            if (!this.beforeAddingTag(tag)) {
                return false;
            }

            // Check if the limit has been reached
            if (this.limit > 0 && this.tags.length >= this.limit) {
                this.$emit('limit-reached');

                return false;
            }

            // Attach the tag if it hasn't been attached yet
            if (!this.tagSelected(tag)) {
                // this.tags.push(tag);
                this.tags = [
                    ...this.tags,
                    tag
                ]

                // Emit events
                this.$nextTick(() => {
                    this.$emit('tag-added', tag);
                    this.$emit('tags-updated');
                });
            }
        },

        /**
         * Remove the last tag in the tags array.
         *
         * @returns void
         */
        removeLastTag() {
            if (!this.input.length && this.deleteOnBackspace && this.tags.length) {
                this.removeTag(this.tags.length - 1);
            }
        },

        /**
         * Remove the selected tag at the specified index.
         *
         * @param index
         * @returns void
         */
        removeTag(index) {
            let tag = this.tags[index];

            if (!this.beforeRemovingTag(tag)) {
                return false;
            }

            this.tags.splice(index, 1);

            // Emit events
            this.$nextTick(() => {
                this.$emit('tag-removed', tag);
                this.$emit('tags-updated');

                if (this.typeaheadAlwaysShow) {
                    this.searchTag();
                }
            });
        },

        /**
         * Search the currently entered text in the list of existing tags
         *
         * @returns void | Boolean
         */
        searchTag() {
            if (this.typeahead !== true) {
                return false;
            }

            if (!(this.oldInput != this.input || (!this.searchResults.length && this.typeaheadActivationThreshold == 0) || this.typeaheadAlwaysShow || this.typeaheadShowOnFocus)) {
                return false;
            }

            this.searchResults = [];
            this.searchSelection = 0;
            let input = this.input.trim();

            if (input.length >= this.typeaheadActivationThreshold || this.typeaheadActivationThreshold == 0 || this.typeaheadAlwaysShow) {
                // Find all the existing tags which include the search text
                const searchQuery = this.escapeRegExp(
                    this.caseSensitiveTags ? input : input.toLowerCase()
                );

                // Search the existing collection
                this.doSearch(searchQuery);
            }

            this.oldInput = this.input;
        },

        /**
         * Perform the actual search
         *
         * @param string searchQuery
         * @return void
         */
        doSearch(searchQuery) {
            for (let tag of this.existingTags) {
                const compareable = this.caseSensitiveTags
                    ? tag.value
                    : tag.value.toLowerCase();

                if (compareable.search(searchQuery) > -1 && ! this.tagSelected(tag)) {
                    this.searchResults.push(tag);
                }
            }

            // Sort the search results alphabetically
            if (this.sortSearchResults) {
                this.searchResults.sort((a, b) => {
                    if (a.value < b.value) return -1;
                    if (a.value > b.value) return 1;

                    return 0;
                });
            }

            // Shorten Search results to desired length
            if (this.typeaheadMaxResults > 0) {
                this.searchResults = this.searchResults.slice(
                    0,
                    this.typeaheadMaxResults
                );
            }
        },

        /**
         * Hide the typeahead if there's nothing intered into the input field.
         *
         * @returns void
         */
        hideTypeahead() {
            if (! this.input.length) {
                this.$nextTick(() => {
                    this.clearSearchResults();
                });
            }
        },

        /**
         * Select the next search result in typeahead.
         *
         * @returns void
         */
        nextSearchResult() {
            if (this.searchSelection + 1 <= this.searchResults.length - 1) {
                this.searchSelection++;
            }
        },

        /**
         * Select the previous search result in typeahead.
         *
         * @returns void
         */
        prevSearchResult() {
            if (this.searchSelection > 0) {
                this.searchSelection--;
            }
        },

        /**
         * Clear/Empty the search results.
         *
         * @reutrns void
         */
        clearSearchResults(returnFocus = false) {
            this.searchResults = [];
            this.searchSelection = 0;

            if (this.typeaheadAlwaysShow) {
                this.$nextTick(() => {
                    this.searchTag();
                });
            }

            if (returnFocus) {
                this.$refs['taginput'].focus();
            }
        },

        /**
         * Clear the list of selected tags.
         *
         * @returns void
         */
        clearTags() {
            this.tags.splice(0, this.tags.length);
        },

        /**
         * Replace the currently selected tags with the tags from the value.
         *
         * @returns void
         */
        tagsFromValue() {
            if (this.value && this.value.length) {
                if (!Array.isArray(this.value)) {
                    console.error('Voerro Tags Input: the v-model value must be an array!');

                    return;
                }

                let tags = this.value;

                // Don't update if nothing has changed
                if (this.tags == tags) {
                    return;
                }

                this.clearTags();

                for (let tag of tags) {
                    this.addTag(tag);
                }
            } else {
                if (this.tags.length == 0) {
                    return;
                }

                this.clearTags();
            }
        },

        /**
         * Check if a tag is already selected.
         *
         * @param tag
         * @returns Boolean
         */
        tagSelected(tag) {
            if (this.allowDuplicates) {
                return false;
            }

            if (! tag) {
                return false;
            }

            const searchQuery = this.escapeRegExp(
                this.caseSensitiveTags ? tag.value : tag.value.toLowerCase()
            );

            for (let selectedTag of this.tags) {
                const compareable = this.caseSensitiveTags
                    ? selectedTag.value
                    : selectedTag.value.toLowerCase();

                if (selectedTag.key === tag.key && this.escapeRegExp(compareable).length == searchQuery.length && compareable.search(searchQuery) > -1) {
                    return true;
                }
            }

            return false;
        },

        /**
         * Clear the input.
         *
         * @returns void
         */
        clearInput() {
            this.input = '';
        },

        /**
         * Process all the keyup events.
         *
         * @param e
         * @returns void
         */
        onKeyUp(e) {
            this.$emit('keyup', e);
        },

        /**
         * Process all the keydown events.
         *
         * @param e
         * @returns void
         */
        onKeyDown(e) {
            this.$emit('keydown', e);
        },

        /**
         * Process the onfocus event.
         *
         * @param e
         * @returns void
         */
        onFocus(e) {
            this.$emit('focus', e);

            this.isActive = true;
        },

        /**
         * Process the onClick event.
         *
         * @param e
         * @returns void
         */
        onClick(e) {
            this.$emit('click', e);

            this.isActive = true;

            this.searchTag();
        },

        /**
         * Process the onblur event.
         *
         * @param e
         * @returns void
         */
        onBlur(e) {
            this.$emit('blur', e)

            if (this.addTagsOnBlur) {
                // Add the inputed tag
                this.tagFromInput(true);
            }

            if (!this.typeaheadAlwaysShow) {
                this.hideTypeahead();
            } else {
                this.searchTag();
            }

            this.isActive = false;
        },
    }
}
</script>
