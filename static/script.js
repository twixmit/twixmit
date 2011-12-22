function twixmitMainReady(){
    window.saveResultsDom = $("#save-results");
    window.textToSave = $("#text-to-save");
    window.postResubmit = $("#checkbox-resubmit");
    window.postButton = $("button#post");
    
    window.yoursPendingList = $("ul#yours-pending");
    window.theirsPendingList = $("ul#theirs-pending");
    window.postBoxToClone = $("li#cloneme");
    
    $("form#post-form").unbind("submit");
    
    postButton.click(savePostForMix);
    
    loadYoursPending();
    loadTheirsPending();
    
    setupPostLoadTimers();
}

function setupPostLoadTimers(){
    setInterval("loadYoursPending()",30000);
    setInterval("loadTheirsPending()",30000);
}

function loadPostsAll(which,cursorWindowKey,prependToList,noPostsText){
    var options = {
        dataType : "json",
        data : {"which" : which ,"since" : window[cursorWindowKey] },
        success : function(data, textStatus, jqXHR){
            if (data.c != "None"){
                window[cursorWindowKey] = data.c;
            }
            
            if(data.r && data.r.length > 0){
                for( result in data.r){
                    
                    if (data.r[result].id && data.r[result].id != ""){
                        var liDom = postBoxToClone.clone();
                        liDom.children(".text").text(data.r[result].text);
                        liDom.children(".time").text(data.r[result].created);
                        liDom.children(".by").text("@" + data.r[result].by_user);
                        liDom.children(".resubmit").text("resubmit? " + data.r[result].resubmit);
                        liDom.removeAttr("id");
                        liDom.prependTo(prependToList);
                        liDom.fadeIn('slow');
                    } else {
                        if( console && console.log){
                            console.log("bad post result: %s",data.r[result])
                        }
                    }
                }
                
                if (prependToList.listView){
                    prependToList.listview('refresh');
                }
            } else {
                
                if(prependToList.children().length == 0){
                    var liDom = postBoxToClone.clone();
                    liDom.children(".text").text(noPostsText);
                    liDom.show();
                    liDom.prependTo(prependToList);
                }
            }
        },
        error : function(jqXHR, textStatus, errorThrown){
            console.error(errorThrown);                  
        },
        url : "/getposts",
        type : "get"
    };
    
    $.ajax(options);

}

function loadYoursPending(){   
    loadPostsAll("yours-pending","yoursPendingListCursor",yoursPendingList,"You have no pending posts, share something!");
}

function loadTheirsPending(){
    loadPostsAll("theirs-pending","theirsPendingListCursor",theirsPendingList,"They have no pending posts, tell them to share something!");
}   
    
function savePostForMix(e){
    var options = {
        dataType : "json",
        data : {"text" : textToSave.val(), "resubmit" : window.postResubmit.prop("checked") },
        success : function(data, textStatus, jqXHR){
                
            if (data && data.success == true){
                saveResultsDom.css("color","green").css("font-weight","bold");
                saveResultsDom.text("Saved!");
                textToSave.val("");
            } else if (data){
                saveResultsDom.css("color","red").css("font-weight","bold");
                saveResultsDom.text(data.failure_message);
            } else {
                saveResultsDom.css("color","red").css("font-weight","bold");
                saveResultsDom.text(textStatus);
            }
        },
        error : function(jqXHR, textStatus, errorThrown){
                saveResultsDom.css("color","red").css("font-weight","bold");
                saveResultsDom.text(errorThrown);
        },
        url : "/saveformix",
        type : "post",
        beforeSend : function(jqXHR, settings){
            postButton.attr("disabled","disabled");
        },
        complete: function(jqXHR, textStatus){
            postButton.removeAttr("disabled");
        }
    };
    
    $.ajax(options);
}