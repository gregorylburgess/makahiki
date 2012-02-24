Namespace("org.wattdepot.gdata.makahiki");

// Creates a visualization showing actual consumption so far today, goal consumption for so far today, and a stoplight (red, green, yellow).
org.wattdepot.gdata.makahiki.EnergyGoalGame = function() {

  // Returns the row in which source's data is located, or -1 if not found.
  function findRow(datatable, source) {
    for (var i = 0; i < datatable.getNumberOfRows(); i++) {
      if (datatable.getValue(i, 0) == source) {
        return i;
      }
    }
    return -1;
  }

  // Draws the components (actual, stoplight, goal, caption) of the energy goal game visualization.
  function draw(id, source, datatable, options) {
    // Define look and feel parameters using options object to override defaults. 
    var width = options.width || 300;
    var backgroundColor = options.backgroundColor || "F5F3E5";
    var globalStyle = options.globalStyle || {};
    var titleStyle = options.titleStyle || {};
    var captionStyle = options.captionStyle || {};

    // Obtain the data from the table, formatting the timestamp.
    var dateFormatter = new google.visualization.DateFormat({pattern: 'MM/dd/yy h:mm:ss a'});
    dateFormatter.format(datatable, 1);
    var row = findRow(datatable, source);
    var tstamp = datatable.getFormattedValue(row,1);
    var actualConsumption = parseInt(datatable.getValue(row,2));
    var goalConsumption = parseInt(datatable.getValue(row,3));
    var warningConsumption = parseInt(datatable.getValue(row,4));
    //console.log(tstamp + ' ' + actualConsumption + ' ' + goalConsumption + ' ' + warningConsumption);

    // Now generate the strings to be put in each cell of the overall table.
    // Next steps:
    //  (a) implement remaining functions.
    //  (b) delete unnecessary functions and commit changes.
    //  (c) decide on options (if any)
    //  (c) update wiki 
    //  (d) create new dist of wattdepot-gdata, update properties file and upload
    var actualConsumptionCell = makeActualConsumptionCell(actualConsumption);
    var goalConsumptionCell = makeGoalConsumptionCell(goalConsumption);
    var stoplightCell = makeStoplightCell(actualConsumption, goalConsumption, warningConsumption);
    var captionCell = makeCaptionCell(actualConsumption, goalConsumption, warningConsumption);

    // Now assemble to HTML table in its entirety
    var goalTable = makeGoalTable(actualConsumptionCell, goalConsumptionCell, stoplightCell, captionCell, backgroundColor, tstamp);
    // Get the top-level div where this visualization should go.
    element = document.getElementById(id);
    element.innerHTML = goalTable;
  }

  // Create the overall HTML table
  function makeGoalTable(actualConsumptionCell, goalConsumptionCell, stoplightCell, captionCell, backgroundColor, tstamp) {

    var goalTable = 
    '<table cellpadding="5" style="background-color: ' + backgroundColor + '; font-family: sans-serif; text-align: center; vertical-align: top" >' +
      '<tr>' +
      '<td style="vertical-align: top" align="center">' + actualConsumptionCell + '</td>' +
      '<td>' + stoplightCell + '</td>' +
      '<td style="vertical-align: top" align="center">' + goalConsumptionCell + '</td>' +
      '</tr>' +
      '<tr> <td colspan="3" style="font-size: 0.8em">' + captionCell + '</td> </tr>' +
      '<tr> <td colspan="3" style="font-size: 0.7em">Last check: ' + tstamp + '</td> </tr>' +
      '</table>';
    return goalTable;
  }

  // Create the caption cell string.
  function makeCaptionCell(actualConsumption, goalConsumption, warningConsumption) {
    var caption;
    if (actualConsumption > goalConsumption) {
      caption = "Your lounge is currently over the goal by " + (actualConsumption - goalConsumption) + " kWh.  See below for ways to conserve.";
    }
    else if (actualConsumption > warningConsumption) {
      caption = "Your lounge is currently making the goal, but just barely ( " + (goalConsumption - actualConsumption) + " kWh).  See below for ways to conserve.";
    }
    else {
      caption = "Your lounge is currently beating the goal by " + (goalConsumption - actualConsumption) + " kWh. Great job!";
    }
    return caption;
  }
  


  // Create the stoplight cell string, which is an <img> tag to the appropriate stoplight image.
  function makeStoplightCell(actualConsumption, goalConsumption, warningConsumption) {
    var stoplightFile;
    if (actualConsumption > goalConsumption) {
      stoplightFile = "stop_light_red.png";
    }
    else if (actualConsumption > warningConsumption) {
      stoplightFile = "stop_light_yellow.png";
    }
    else {
      stoplightFile = "stop_light_green.png";
    }
    return '<img src="/site_media/static/images/energy/' + stoplightFile + '" />';
  }


  // Create the actual consumption HTML string.
  function makeActualConsumptionCell(actualConsumption) {
    var cell = '<table cellpadding="5">';
    cell = cell + '<tr><td valign="top" style="text-align: center; vertical-align: top">Consumption Today <br>(So Far)</td></tr>';
    cell = cell + '<tr><td style="text-align: center; font-size: 2.5em; font-weight: bold">' + actualConsumption + ' kWh</td></tr>';
    cell = cell + '</table>';
    return cell;
  }

  // Create the goal consumption HTML string.
  function makeGoalConsumptionCell(goalConsumption) {
    var cell = '<table cellpadding="5">';
    cell = cell + '<tr><td valign="top" style="text-align: center; vertical-align: top">Goal for Today <br>(So Far)</td></tr>';
    cell = cell + '<tr><td style="text-align: center; font-size: 2.5em; font-weight: bold">' + goalConsumption + ' kWh</td></tr>';
    cell = cell + '</table>';
    return cell;
  }

  return {
    // Public interface to this function.
    draw : draw
  };
};
