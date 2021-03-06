/** @jsx React.DOM */
/* global require, module */
(function() {
  'use strict';

  var React = require('react/addons'),
      WorkflowForm = require('./workflowform'),
      CaptureInterface = require('./capture'),
      WorkflowDetails = require('./workflow'),
      WorkflowList = require('./workflowlist'),
      NavigationBar = require('./navbar'),
      LogDisplay = require('./logdisplay.js'),
      fnAlert = require('./foundation').alert;

  /**
   * Core application component.
   *
   * Handles selection of display components and error messages.
   *
   * @property {Backbone.Collection<Workflow>} [workflows] - Associated workflows
   * @property {number} [workflowId] - Associated workflow ID
   * @property {string} view - Name of view to display
   * @property {Backbone.Collection<Message>} messages - Messages to display
   */
  module.exports = React.createClass({
    /** Register message change listeners */
    componentDidMount: function() {
      this.props.messages.on('add change remove',
                             this.forceUpdate.bind(this, null));
    },
    /**
     * Get title for navigation bar.
     *
     * @param {string} viewName - name of current view
     * @return {string} The title for the navigation bar
     */
    getNavTitle: function(viewName) {
      var mappings = {
        create:       "spreads: new workflow",
        capture:      "spreads: capture",
        preferences:  "spreads: preferences",
        view:         "spreads: details"
      };
      if (mappings[viewName] !== undefined) {
        return mappings[viewName];
      } else {
        return "spreads";
      }
    },
    /**
     * Get view component to render.
     *
     * @param {string} viewName - name of current view
     * @return {React.Component} The component to render
     */
    getViewComponent: function(viewName) {
      var workflows = this.props.workflows,
          workflowId = this.props.workflowId;
      switch (viewName) {
      case "create":
        var newWorkflow = new workflows.model(null, {collection: workflows});
        return <WorkflowForm workflow={newWorkflow}/>;
      case "capture":
        return <CaptureInterface workflow={workflows.get(workflowId)}/>;
      case "view":
        return <WorkflowDetails workflow={workflows.get(workflowId)}/>;
      case "log":
        return <LogDisplay />;
      default:
        return <WorkflowList workflows={workflows}/>;
      }
    },
    /**
     * Get a callback to close a given message
     *
     * @param {Message} message - The message to close in the callback
     * @return {function} - A callback function that closes the `message`.
     */
    getCloseMessageCallback: function(message) {
      return function() {
        this.props.messages.remove([message]);
      }.bind(this);
    },
    render: function() {
      var navTitle = this.getNavTitle(this.props.view),
          viewComponent = this.getViewComponent(this.props.view);
      return (
        <div>
          <NavigationBar title={navTitle} />
          {this.props.messages &&
              this.props.messages.map(function(message) {
              return (
                  <fnAlert level={message.get('level')}
                          message={message.get('message')}
                          closeCallback={this.getCloseMessageCallback.bind(this)(message)}>
                  <a className="right" href='#/log'>(View detailed log)</a>
                  </fnAlert>);
              }, this)}
          {viewComponent}
        </div>
      );
    }
  });
}());
