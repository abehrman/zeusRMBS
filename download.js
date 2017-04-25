var data = source.data;
var filetext = 'Month,Beginning Balance,SMM, Mortgage Payments, ' +
    'Net Interest, Scheduled Principal, Prepayments, ' +
    'Total Principal, Cash Flow\n';
for (i = 0; i < data['periods'].length; i++) {
    var currRow = [data['periods'][i].toString(),
        data['beginning_balance'][i].toString(),
        data['SMM'][i].toString(),
        data['mortgage_payments'][i].toString(),
        data['net_interest'][i].toString(),
        data['scheduled_principal'][i].toString(),
        data['prepayments'][i].toString(),
        data['total_principal'][i].toString(),
        data['cash_flow'][i].toString().concat('\n')];

    var joined = currRow.join();
    filetext = filetext.concat(joined);
}

var filename = 'data_result.csv';
var blob = new Blob([filetext], {type: 'text/csv;charset=utf-8;'});

//addresses IE
if (navigator.msSaveBlob) {
    navigator.msSaveBlob(blob, filename);
}

else {
    var link = document.createElement("a");
    link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = filename;
    link.target = "_blank";
    link.style.visibility = 'hidden';
    link.dispatchEvent(new MouseEvent('click'))
}