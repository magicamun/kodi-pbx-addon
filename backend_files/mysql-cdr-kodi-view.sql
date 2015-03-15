drop view if exists cdr_kodi;
create view cdr_kodi (
        accountcode,
        src,
        dst,
        dcontext,
        clid,
        channel,
        dstchannel,
        lastapp,
        lastdata,
        start,
        answer,
        end,
        duration,
        billsec,
        disposition,
        amaflags,
        uniqueid,
        userfield
)
as select
        cdr.accountcode,
        cdr.src,
        cdr.dst,
        cdr.dcontext,
        cdr.clid,
	cdr.channel,
        cdr.dstchannel,
        cdr.lastapp,
        cdr.lastdata,
        UNIX_TIMESTAMP(cdr.calldate),
	UNIX_TIMESTAMP(cdr.calldate + (cdr.duration - cdr.billsec)),
	UNIX_TIMESTAMP(cdr.calldate + cdr.duration),
	cdr.duration,
        cdr.billsec,
        cdr.disposition,
        cdr.amaflags,
        cdr.uniqueid,
        cdr.userfield
from cdr;