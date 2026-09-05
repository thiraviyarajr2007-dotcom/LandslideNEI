
      function uninit()
      {
		parent.removealllayer();
	parent.removepop("#help1");
   parent.removepop("#help2");
    parent.removepop("#help3");   
	if(parent.popup)
	parent.popup.destroy();
	viewwarn('Remove');
	//parent.$("#mapwarni").html('');	
  //  parent.$("#mapwarnq").html('');	
  document.getElementById('mapwarnq').innerHTML="";
      }
	  
	
      function handleClick(obj1,obj2)
      {
     
      document.getElementById(obj1).style.display="none";
      document.getElementById(obj2).style.display="";

      }

jQuery(document).ready(function() {
 jQuery(".content").hide();
 jQuery("#t1").next(".content").slideToggle(500); 
  //toggle the componenet with class msg_body
  jQuery(".heading").click(function()
  {
	$(".content").slideUp(1);
	for (var i=1;i<4;i++)
	$("#expandt"+i).attr("src", "../../img/sliderInc.png");
	
	jQuery(this).next(".content").slideToggle(500);
	if(document.getElementById('expand'+this.id))
	{
	if(document.getElementById('expand'+this.id).getAttribute('src')=='../../img/sliderDec.png')
					$("#expand"+this.id).attr("src", "../../img/sliderInc.png");
				else
					$("#expand"+this.id).attr("src", "../../img/sliderDec.png");
	}
  });
});

function statechange()
{
view_remove();
if(document.getElementById('states').value=='Select' || document.getElementById('states').value=="")
{document.getElementById('alyear').innerHTML="<select name='' id='sector'> <option>Select</option> </select>";
document.getElementById('docspan').style.display="none";
return;
}
ajax2("getsector.php?state="+document.getElementById('states').value,"alyear");

}

function ajax2(url,div_name)
	{
	var req = getXMLHTTP();
		
		if (req) {
			
			req.onreadystatechange = function() {
				if (req.readyState == 4) {
					// only if "OK"
					if (req.status == 200) 						
						document.getElementById(div_name).innerHTML=req.responseText;	

				}				
			}			
			req.open("GET", url, true);
			req.send(null);
		} 
				
			
	}
	
	function getXMLHTTP() { //fuction to return the xml http object
		
		var xmlhttp=false;	
		try{
			xmlhttp=new XMLHttpRequest();
		}
		catch(e)	{		
			try{			
				xmlhttp= new ActiveXObject("Microsoft.XMLHTTP");
			}
			catch(e){
				try{
				xmlhttp = new ActiveXObject("Msxml2.XMLHTTP");
				}
				catch(e1){
					xmlhttp=false;
				}
			}
		}
		 	
		return xmlhttp;
    }

	
	function view_remove()
	{
	if(document.getElementById('sector').value == 'Select' ||document.getElementById('sector').value == "")
	document.getElementById('docspan').style.display="none";
	else
	document.getElementById('docspan').style.display="block";
	parent.removelayer('ldhz');
	document.getElementById('viewal').src='img/view.png';
	document.getElementById('legend').style.display="none";
	if(parent.vectors1)
	parent.vectors1.removeAllFeatures();
	if(parent.popup)
	parent.popup.destroy();
	try
	{
	parent.removepop("#help1");
	parent.removepop("#help2");
    parent.removepop("#help3");  
	}
	catch(e)
	{
	}
	}
	
	function view_al()
	{
	var a=document.getElementById('sector').value.split('-');
	
	parent.loadlabellayers_lhz('ldhz',"https://bhuvan-vec2.nrsc.gov.in/bhuvan/wms/",'disaster:'+a[0].split(" ")[0]);
	document.getElementById('legend').style.display="block";
	//setcenter to be given
	var a2=a[1].split(" ");
	parent.zoom_to_layer(a2[0],a2[1],a2[2],a2[3]);
	parent.map.setLayerIndex(parent.rediff_maps, 20);
	parent.map.setLayerIndex(parent.poi_layer, 21);
	ajax2('getroute.php?id='+a[0].split(" ")[0],'zoomto');
		document.getElementById("lhz_map_span").style.display="none";
	}
	
	function metadata()
	{
	var a=document.getElementById('sector').value.split('-');
	parent.load_video('#metadata','get/loading_feedback?q=metatile_lhz.php&id='+a[0].split(" ")[0],'Metadata','520','550');
	}
	
	function webservice()
	{
	var a=document.getElementById('sector').value.split('-');
	parent.load_video('#wmsurl','get/loading_feedback?q=wmsurl/wmsurl_lhz.php&id='+a[0].split(" ")[0],'Webservices URLs','520','550');
	}
	
	function zoomto(dist_vector)
	{

	var d=dist_vector.split("_");
	
	if(dist_vector=='Select' || dist_vector=="")
	{
	if(parent.vectors1) {
	parent.vectors1.removeAllFeatures()
	}
	 if (parent.vectors2) {
            parent.vectors2.removeAllFeatures()
        }
	document.getElementById("lhz_map_span").style.display="none";
	return
	}
	parent.distzoom(d[1],"",true);
	parent.distzoom2(d[0], "");
	var a=document.getElementById('sector').value.split('-');
	document.getElementById("lhz_map").href="../documents/landslide/"+a[0].split(" ")[0]+"/"+d[2]+".pdf";
	document.getElementById("lhz_map_span").style.display="inline";
	}
//For LS early warning

function modifywarn(a,b,c,d,e)
{
$("#warnn").attr("disabled", a);
	//$("#warnr").attr("disabled", b);
	if(b)
	$("#mapwarn").attr("style", "display:none");
	else
	$("#mapwarn").attr("style", "border-radius: 2px;-moz-border-radius: 2px;border:solid #2070cf 2px;padding-bottom:1px;padding-left:1px;padding-right:1px;padding-top:1px;");
	$("#warnp").attr("disabled", c);
	$("#warnl").attr("disabled", d);
$("#warns").attr("disabled", e);
}

	function viewwarn(val)
	{
	if(val=="View")
	{
	var lol=$("#warno").val();
	// if(lol=='Shillong-Aizwal-91.846 23.693 92.86 25.59')
	loadmap("lswarn", "https://bhuvan-ras2.nrsc.gov.in/cgi-bin/ls_warn.exe?fdate="+fdate+"&LAYERS="+warnlayername[ctr]+"hcne", "rishi_kedar_badri");
	// else
	loadmap("lswarn", "https://bhuvan-ras2.nrsc.gov.in/cgi-bin/ls_warn.exe?fdate="+fdate+"&LAYERS="+warnlayername[ctr]+"hc", "rishi_kedar_badri");
	try 
	 {
	 if(parent.$("#notify").dialog( "isOpen" ))
	 parent.$("#notify").load('usrtasks/landslide/legend.php?a='+fdate+"&b="+$("#warnd").html());
	 else
	 parent.load_video('#notify','usrtasks/landslide/legend.php?a='+fdate+"&b="+$("#warnd").html(),'Legend','440','200');
	 }
	 catch(e)
	 {
	  parent.load_video('#notify','usrtasks/landslide/legend.php?a='+fdate+"&b="+$("#warnd").html(),'Legend','440','200');
	 }
	$("#warnv").attr("value", "Remove");
	modifywarn(false,false,false,false,true);
	zoomwarn();
	rainwarn();//for enabling query
	}
	else
	{
	$("#warnv").attr("value", "View");
	modifywarn(true,true,true,true,true);
	parent.removelayer('lswarn');
	if(warnflag==1)
	{
	parent.map.events.unregister('click', parent.map, queryrainwarn);
	warnflag=0;
	}
	}
	}
	
var wloop,ctr=2,warnflag=0,lonlat;
var warnlayername = ["d1", "d2", "d3"];

	function loopwarn()
	{
	modifywarn(true,false,true,true,false);
	wloop=setInterval("warnlayer()", 4000);
	}

	function warnlayer()
	{
	ctr++;
	if(ctr==num)
	ctr=0;
	$("#warnd").html(date[ctr]);
	parent.removelayer('lswarn');
	// var lol=$("#warno").val();
	// if(lol=='Shillong-Aizwal-91.846 23.693 92.86 25.59')
	loadmap("lswarn", "https://bhuvan-ras2.nrsc.gov.in/cgi-bin/ls_warn.exe?fdate="+fdate+"&LAYERS="+warnlayername[ctr]+"hcne", "rishi_kedar_badri");
	// else
	loadmap("lswarn", "https://bhuvan-ras2.nrsc.gov.in/cgi-bin/ls_warn.exe?fdate="+fdate+"&LAYERS="+warnlayername[ctr]+"hc", "rishi_kedar_badri");
	
	 parent.$("#notify").load('usrtasks/landslide/legend.php?a='+fdate+"&b="+$("#warnd").html());
	rainwarn();
	}
	
	function stopwarn()
	{ 
	modifywarn(false,false,false,false,true);
	window.clearInterval(wloop);
	}
	
	function prevwarn()
	{
	if(ctr==(num-1))
	ctr=0;
	else
	ctr=ctr+1;
	warnlayer();
	}
		
	function zoomwarn()
	{
	var a2=($("#warno").val()).split("-")[2].split(" ");
	parent.zoom_to_layer(a2[0],a2[1],a2[2],a2[3]);
	}
	
	function loadmap(displayname, layerurlarray, layername) {

	parent.swipe_layer = new parent.OpenLayers.Layer.WMS(displayname, layerurlarray, {
		layers: layername,
		transparent: true
	},
	{	isBaseLayer: false,
		attribution: " Early Warning generated on "+fdate+" for "+$("#warnd").html(),
	},
	{
	   'diplayInLayerSwitcher':false
	});
	parent.map.addLayer(parent.swipe_layer);
	if(parent.admin_grouped)
	parent.map.setLayerIndex(parent.admin_grouped, 996);
		 
	

}

function legendwarn()
{
  parent.load_video('#notify','usrtasks/landslide/legend.php?a='+fdate+"&b="+$("#warnd").html(),'Legend','440','200');
}

function rainwarn()
{
warnflag=1;
parent.map.events.register('click', parent.map, queryrainwarn);
refreshrainwarn();
}

function refreshrainwarn()
{
//parent.$("#mapwarnq").html('');
document.getElementById('mapwarnq').innerHTML="";
warnmarker(0,0);
}

var ajaxreq;

function queryrainwarn(e)
{
lonlat = parent.map.getLonLatFromViewPortPx(e.xy);
var lol=$("#warno").val();
warnmarker(lonlat.lon,lonlat.lat);
if(ajaxreq)
ajaxreq.abort();
ajaxreq = parent.$.ajax({url:"usrtasks/landslide/getwarnquery.php?l="+lonlat.lat+"&m="+lonlat.lon+"&lol="+lol+"&n="+warnlayername[ctr]+"rf&d="+fdate,success:function(result){
       //  parent.$("#mapwarnq").html(result);	
document.getElementById('mapwarnq').innerHTML=result;	   
}});
}



//onload for rainfall map

function warnmarker(lon,lat)
{


if (parent.feature != null) {	
            parent.vlayer.destroyFeatures(parent.feature);			
        }
if(lon==0 && lat==0)
return;
        parent.feature = new parent.OpenLayers.Feature.Vector(new parent.OpenLayers.Geometry.Point(lon,lat), {
            some: "data"
        }, {
		
            externalGraphic: "img/marker.png",
            graphicHeight: 17,
            graphicWidth: 16
        });   
		
        parent.vlayer.addFeatures(parent.feature);	
}

	

var idinfoid_ls=0;



function ls_identifyinfo(url,layername,id)
{
if(idinfoid_ls!=0)
parent.landslide_removeidentifyinfo();

if($('#identify'+id).attr("src").match("infono.png") )
{
parent.landslide_removeidentifyinfo();
$('#identify'+id).attr("src","img/info.png");
$('#identify'+id).attr("title","Identify Features");
idinfoid_ls=0;
return;
}
var layer="";
for (var b = parent.map.layers, c = 1, length=b.length; c < length; c++) 
if(b[c].name==layername)
layer=b[c];

if(layer=="")
{
alert("Please first overlay the layer");
return;
}
if(layer.getVisibility() == false)
{
alert("Please first overlay the layer");
return;
}

	parent.landslide_identifyinfo(url,layername);
	$('#identify'+id).attr("src","img/infono.png");
	$('#identify'+id).attr("title","Stop Identify Features");
	if(idinfoid_ls!=0)
	{
	$('#identify'+idinfoid_ls).attr("src","img/info.png");
	$('#identify'+idinfoid_ls).attr("title","Identify Features");
	}
	idinfoid_ls=id;
}