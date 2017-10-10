#!/usr/bin/env perl

use strict;
use warnings;
use Getopt::Long;
use Carp;
use Search::Elasticsearch;
use WWW::Mechanize;
use JSON -support_by_pp;
use Data::Dumper;


my $es_host = "ves-hx-e4:9200";
my $es_index_name = 'faang';

GetOptions(
  'es_host=s' =>\$es_host,
  'es_index_name=s' =>\$es_index_name,
);

croak "Need -es_host" unless ($es_host);
print "Working on $es_index_name at $es_host\n";

#get the latest release version
#this requires the immediate deployment of latest release on the production server
my $ruleset_version = &getRulesetVersion();
print "Rule set release: $ruleset_version\n";

#initial ES object
my $es = Search::Elasticsearch->new(nodes => $es_host, client => '1_0::Direct'); #client option to make it compatiable with elasticsearch 1.x APIs

#define what type of data to validate
my @types = qw/organism specimen/;
foreach my $type(@types){
  &validateAllRecords($type);
}

#validate all records in one type
sub validateAllRecords(){
  my $type = $_[0];
  my $tmpOutFile = "${type}_records.json";#the temp middle file
  print "Validating $type data\n";
  #retrieve all records from elastic search server in the chunk of 500
  my $scroll = $es->scroll_helper(
    index => $es_index_name,
    type => $type,
    search_type => 'scan',
    size => 500,
  );
  my $count = 0;
  #the temporary middle output file contains all record from one type
  open OUT,">$tmpOutFile";
  #the top level expected by the validate API is an array. each element is a BioSample record
  print OUT "[\n";
  while (my $loaded_doc = $scroll->next) {
    my $biosampleId = $$loaded_doc{_id};
    $count++;
    my %data = %{$$loaded_doc{_source}};
    my $convertedData = &convert(\%data,$type);
    #convert the middle data structure to json for outputting into the temp file
    my $jsonStr = to_json($convertedData);
    print OUT ",\n" unless ($count==1);
    print OUT "$jsonStr\n";
  }
  print OUT "]\n";
  close OUT;
  #using curl to fill the form, reference page https://curl.haxx.se/docs/manual.html
  my $cmd = 'curl -F "format=json" -F "rule_set_name=FAANG Samples" -F "file_format=JSON" -F "metadata_file=@'.$tmpOutFile.'" "https://www.ebi.ac.uk/vg/faang/validate"';
  my $pipe;
  open $pipe, "$cmd|"; #send the file to the server and receive the response
  my $response = &readHandleIntoString($pipe);
  my $json = &decode_json($response);
  &printValidatationResult($$json{entities},$type);
}

#convert ES record to the data structure expected by the API
#a hash which has id, entity_type and attributes as its keys (validate-metadata repo Bio/Metadata/Entity)
#most fields should be saved as one element in the attributes array
#every element expects name, value, units, uri and id (Bio/Metadata/Attribute.pm) 
sub convert(){
  my %data = %{$_[0]};
  my $type = $_[1];
  my @keys = sort keys %data;
  $"=">,<";
  my @attr;
  my %result;
  $result{entity_type}="sample";
  $result{id}=$data{biosampleId};
  my $material = $data{material}{text};
  #delete the extra keys which are not in the ruleset  
  delete $data{releaseDate};
  delete $data{updateDate};
  delete $data{organization};
  delete $data{biosampleId};
  delete $data{name};

  my %typeSpecific;
  if($type eq "organism"){
    @attr = &parse(\@attr,\%data,$type);
  }else{
    #delete the data sections which were created for sorting purpose in the frontend or similar purpose and are NOT in the rule set
    #the following two are specimen only
    delete $data{cellType};
    delete $data{organism};
    my $typeSpecific = &toLowerCamelCase($material);
    if (exists $data{$typeSpecific}){
      %typeSpecific = %{$data{$typeSpecific}};
      delete $data{$typeSpecific};
    }else{
      print "Error: type specific data not found for $result{id} (type $material)\n";
      return;
    }
    @attr = &parse(\@attr,\%data,$type);
    @attr = &parse(\@attr,\%typeSpecific,$type);
  }

  @{$result{attributes}}= @attr;
  return \%result;
}

sub parse(){
  my @attr = @{$_[0]};
  my %data = %{$_[1]};
  my $type = $_[2];
  foreach my $key(keys %data){
#    next if ($key eq "organization");
    my $refType = ref($data{$key});
    #according to ruleset https://www.ebi.ac.uk/vg/faang/rule_sets/FAANG%20Samples
    #only organism.healthStatus, organism.childOf, specimenFromOrganism.healthStatusAtCollection, poolOfSpecimen.derivedFrom,
    #cellSpecimen.cellType are of array type (i.e. having multiple values)
    #for array, each element has a corresponding entry directly under attributes array, not forming an array of the same field
    if ($refType eq "ARRAY"){
      my %hash;
      my $matched = &fromLowerCamelCase($key);
      $matched = "Child of" if ($key eq "childOf");
      foreach my $elmt(@{$data{$key}}){
        if (ref($elmt) eq "HASH"){
          my %hash = &parseHash($elmt,$matched,$type);#the hash itself, value used as name, organism or specimen
          push(@attr,\%hash);
        }else{
          my %hash = (
            name => $matched,
            value => $elmt
          );
          push(@attr,\%hash);
        }
      }
    }elsif($refType eq "HASH"){
      my %hash = &parseHash($data{$key},$key,$type);
      push(@attr,\%hash);
    }else{#scalar
      my %tmp;
      $tmp{name}=&fromLowerCamelCase($key); 
      #these hard-coding are for the fields with special capitalization case or conserved field name in the rule set (check the name field)
      #https://github.com/FAANG/faang-metadata/blob/master/rulesets/faang_samples.metadata_rules.json
      $tmp{name} = "Sample Description" if ($key eq "description");
      $tmp{name} = "Derived from" if ($key eq "derivedFrom");
      $tmp{value} = $data{$key};
      push(@attr,\%tmp);
    }
  }
  return @attr;
}

sub parseOntologyTerm(){
  my $uri = $_[0];
  my $idx = rindex($uri,"\/");
  my $id = substr($uri,$idx+1);
  $id =~s/:/_/; #some ontology id use : as the separator
  $id = "OBI_0100026" if ($id eq "UBERON_0000468");#some biosample records wrongly assigned the ontology id to organism by the submitter
  my ($source) = split ("_",$id);#ontology library, e.g. PATO, EFO, normally could be extract from ontology id
  #this is only part of the hash which will be populated after being returned (name, value, units)
  my %result = (
    id => $id,
    source_ref => $source
  );
  return %result;
}
#should be the same as ucfirst
sub capitalizationFirstLetter(){
  my $in = $_[0];
  if (length $in < 2){
    return uc $in;
  }else{
    my $first = substr($in,0,1);
    my $remaining = substr($in,1);
    return uc($first).$remaining;
  }
}

sub parseHash(){
  my %hash = %{$_[0]};
  my $key = $_[1];
  my $type = $_[2];
  my %tmp;
  if (exists $hash{ontologyTerms}){
    %tmp = &parseOntologyTerm($hash{ontologyTerms}) if (length $hash{ontologyTerms});#in 5.12, length $var retur undef when $var undefined
  }
  $tmp{units} = $hash{unit} if (exists $hash{unit});
  if (exists $hash{url}){
    $tmp{value} = $hash{url};
    $tmp{uri} = $hash{url} ;
    $key = &fromLowerCamelCase($key);
  }else{
#    $key = &capitalizationFirstLetter($key);
    if ($key eq "material"){
      $key = "Material";
    }else{
      $key = &fromLowerCamelCase($key);
    }
    $tmp{value} = $hash{text};
  }
  $tmp{name} = $key;
  return %tmp;
}
#convert phrase in lower camel case to words separated by space
sub fromLowerCamelCase(){
  my $str = $_[0];
  my @arr = split(/(?=[A-Z])/,$str);
  return lc(join (" ",@arr));
}
#convert a string containing _ or space into lower camel case
sub toLowerCamelCase(){
  my $str = $_[0];
  $str=~s/_/ /g; 
  $str =~ s/^\s+|\s+$//g;
  $str = lc ($str);
  $str =~s/ +(\w)/\U$1/g;
  return $str;
}

sub printValidatationResult(){
  my @entities = @{$_[0]};
  my $type = $_[1];
  my @status = qw/pass warning error/;
  my %summary;
  foreach my $entity(@entities){
    my %hash= %{$entity};
    my $status = $hash{_outcome}{status};
    $summary{$status}++;
    next unless ($status eq "error");#only print error messages.
    print "$hash{id}\t$type\t$status\t";
    if ($status eq "pass"){
      print "\n";
      next;
    }
    #if the warning related to columns not existing in the data, the following attribute iteration will not go through that column
    my $backupMsg = "";
    my $tag = $status."s";
    $backupMsg = join (";",@{$hash{_outcome}{$tag}}) if (exists $hash{_outcome}{$tag});
    my @msgs;
    my @attributes = @{$hash{attributes}};
    foreach my $attr (@attributes){
      next if ($$attr{_outcome}{status} eq "pass");
      $tag = $$attr{_outcome}{status}."s";
      my $msg = "$$attr{name}:".$$attr{_outcome}{$tag}[0];
      push (@msgs,$msg);
    }
    my $totalMsg = join (";",@msgs);
    $totalMsg = $backupMsg if (scalar @msgs == 0);
    print "$totalMsg\n";
  }
  print "Summary:\n";
  foreach (@status){
    if (exists $summary{$_}){
      print "$_\t$summary{$_}\n";
    }else{
      print "$_\t0\n";
    }
  }
  print "\n";
}
#retrieve release number from GitHub via API
sub getRulesetVersion(){
  my $cmd = 'curl https://api.github.com/repos/FAANG/faang-metadata/releases';
  my $pipe;
  open $pipe, "$cmd|";
  my $response = &readHandleIntoString($pipe);
  my $json = &decode_json($response);
  my $current = $$json[0];
  return $$current{tag_name};
}
#read the content from the file handle and concatenate into a string
#for development purpose of reading several records from a file
sub readHandleIntoString(){
  my $fh = $_[0]; 
  my $str = "";
  while (my $line = <$fh>) {
    chomp($line);
    $str .= $line;
  }
  return $str;
}
